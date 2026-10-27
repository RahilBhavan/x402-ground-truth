"""Slice 3: the keyless census over x402scan's complete 3.5-hour buckets, one bucket at a time, resumable.

Each bucket's rows go into out/settlements.sqlite in one transaction with a `done` mark, so a rerun skips
finished buckets and an interrupted bucket starts over cleanly. RPC batches inside a bucket run in parallel.

x402scan counts every USDC transfer in a transaction a listed address sent, marker or not. Transactions with an x402
marker are found from logs; the rest are found from each address's nonce, by bisecting only the block ranges where
the nonce rose more than the marked transactions explain.
"""
import bisect
import calendar
import os
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import channels as channel_lookup
from . import pipeline
from .constants import PROXIES, TOPIC_AUTHORIZATION_USED, TOPIC_BATCH_CLAIMED, USDC
from .hour import block_at
from .settlements import classify

WORKERS = int(os.environ.get("GROUND_TRUTH_WORKERS", 2))  # publicnode rate-limited 8 and then 3 parallel batches (HTTP 429)
KEEP = {USDC, *PROXIES.values()}

SCHEMA = """
create table if not exists buckets (bucket_start text primary key, first_block int, last_block int,
  x402scan_transfers int, x402scan_atomic int, done int default 0, meta text);
create table if not exists transfers (tx text, log_index int, payer text, payee text, atomic int, facilitator text,
  sender text, synced int, bucket_start text, primary key (tx, log_index));
create table if not exists w0 (tx text, log_index int, payer text, payee text, atomic int, facilitator text,
  sender text, synced int, bucket_start text, primary key (tx, log_index));
create table if not exists payments (tx text, log_index int, payer text, payee text, via text, atomic int, scheme text,
  facilitator text, sender text, synced int, bucket_start text, primary key (tx, log_index));
create table if not exists removed (tx text, log_index int, payer text, payee text, atomic int, reason text,
  facilitator text, sender text, synced int, bucket_start text, primary key (tx, log_index));
"""


def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def parse(s):
    return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))


def complete_buckets(capture):
    """x402scan's buckets minus the partial first and last ones."""
    rows = json.loads(Path(capture).read_text())["bucketed"]["data"]
    return [{"start": parse(r["bucket_start"]), "transfers": r["total_transactions"], "atomic": r["total_amount"]}
            for r in rows[1:-1]]


def shrink_tx(t):
    return {"hash": t["hash"], "from": t["from"]}


def shrink_receipt(r):
    return {"transactionHash": r["transactionHash"], "status": r["status"],
            "logs": [{k: l[k] for k in ("address", "topics", "data", "logIndex")}
                     for l in r["logs"] if l["address"].lower() in KEEP]}


def parallel(rpc, method, hashes, shrink):
    chunks = [hashes[i:i + pipeline.RPC_BATCH] for i in range(0, len(hashes), pipeline.RPC_BATCH)]
    with ThreadPoolExecutor(WORKERS) as pool:
        parts = pool.map(lambda c: rpc.batch([(method, [h]) for h in c], label=f"{method} x{len(c)}", shrink=shrink),
                         chunks)
    return [r for part in parts for r in part]


def parallel_logs(rpc, address, topic0, first, last):
    spans = [(a, min(a + pipeline.CHUNK - 1, last)) for a in range(first, last + 1, pipeline.CHUNK)]
    with ThreadPoolExecutor(WORKERS) as pool:
        parts = pool.map(lambda s: pipeline.logs(rpc, address, topic0, *s), spans)
    return [l for part in parts for l in part]


def nonces(rpc, addresses, block):
    calls = [("eth_getTransactionCount", [a, hex(block)]) for a in addresses]
    out = []
    for i in range(0, len(calls), pipeline.RPC_BATCH):
        out += rpc.batch(calls[i:i + pipeline.RPC_BATCH], label=f"nonces at {block}")
    return dict(zip(addresses, (int(n, 16) for n in out)))


def gap_blocks(rpc, address, lo, hi, n_lo, n_hi, known):
    """Blocks in (lo, hi] where `address` sent more transactions than the sorted block list `known` holds."""
    explained = bisect.bisect_right(known, hi) - bisect.bisect_right(known, lo)
    if n_hi - n_lo <= explained:
        return []
    if hi - lo == 1:
        return [hi]
    mid = (lo + hi) // 2
    n_mid = int(rpc.call("eth_getTransactionCount", [address, hex(mid)], label=f"nonce {address[:10]} {mid}"), 16)
    return gap_blocks(rpc, address, lo, mid, n_lo, n_mid, known) + gap_blocks(rpc, address, mid, hi, n_mid, n_hi, known)


def unmarked(rpc, first, last, facilitators, known):
    """Hashes of facilitator-sent transactions in [first, last] that no marker log named. known: {sender: [block]}."""
    addresses = sorted(facilitators)
    start, end = nonces(rpc, addresses, first - 1), nonces(rpc, addresses, last)
    todo = [a for a in addresses if end[a] - start[a] > len(known.get(a, ()))]
    with ThreadPoolExecutor(WORKERS) as pool:
        found = pool.map(lambda a: gap_blocks(rpc, a, first - 1, last, start[a], end[a], sorted(known.get(a, ()))), todo)
    blocks = sorted({b for part in found for b in part})
    shrink = lambda b: [shrink_tx(t) for t in b["transactions"] if t["from"].lower() in facilitators]
    return [t for part in parallel_blocks(rpc, blocks, shrink) for t in part]


def parallel_blocks(rpc, blocks, shrink):
    chunks = [blocks[i:i + 10] for i in range(0, len(blocks), 10)]
    with ThreadPoolExecutor(WORKERS) as pool:
        parts = pool.map(lambda c: rpc.batch([("eth_getBlockByNumber", [hex(b), True]) for b in c],
                                             label=f"blocks x{len(c)}", shrink=shrink), chunks)
    return [r for part in parts for r in part]


def bucket_rows(rpc, first, last, facilitators):
    marker = parallel_logs(rpc, USDC, TOPIC_AUTHORIZATION_USED, first, last)
    proxy = {k: parallel_logs(rpc, a, None, first, last) for k, a in PROXIES.items()}
    block = {l["transactionHash"]: int(l["blockNumber"], 16) for l in marker + [l for v in proxy.values() for l in v]}
    hashes = sorted(block)
    sender = {t["hash"]: t["from"].lower() for t in parallel(rpc, "eth_getTransactionByHash", hashes, shrink_tx)}
    fac_hashes = sorted(h for h in hashes if sender[h] in facilitators)
    known = {}
    for h in fac_hashes:
        known.setdefault(sender[h], []).append(block[h])
    extra = [t for t in unmarked(rpc, first, last, facilitators, known) if t["hash"] not in block]
    sender.update({t["hash"]: t["from"].lower() for t in extra})
    receipts = parallel(rpc, "eth_getTransactionReceipt", fac_hashes + sorted(t["hash"] for t in extra), shrink_receipt)
    claim_ids = {l["topics"][1].lower() for l in proxy["batch_settlement"] if l["topics"][0] == TOPIC_BATCH_CLAIMED}
    chans = channel_lookup.lookup(rpc, claim_ids, last)
    rows = {"transfers": [], "w0": [], "payments": [], "removed": []}
    for r in receipts:
        out = classify(r, sender[r["transactionHash"]], facilitators, chans)
        for k in rows:
            rows[k] += out[k]
    meta = {"authorization_used_logs": len(marker), "proxy_logs": {k: len(v) for k, v in proxy.items()},
            "facilitator_txs": len(fac_hashes), "unmarked_facilitator_txs": len(extra), "batch_channels_resolved": f"{len(chans)}/{len(claim_ids)}"}
    return rows, meta


def run(rpc, capture, db_path, facilitators, log=print):
    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    for b in complete_buckets(capture):
        start = iso(b["start"])
        if db.execute("select done from buckets where bucket_start = ?", (start,)).fetchone() == (1,):
            continue
        first, last = block_at(rpc, b["start"]), block_at(rpc, b["start"] + 12_600) - 1
        t0 = time.time()
        rows, meta = bucket_rows(rpc, first, last, facilitators)
        with db:  # one transaction per bucket: all rows and the done mark, or nothing
            for table in rows:
                db.execute(f"delete from {table} where bucket_start = ?", (start,))
            tail = lambda r: (r["facilitator"], r["sender"], int(r["x402scan_synced"]), start)
            for table in ("transfers", "w0"):
                db.executemany(f"insert into {table} values (?,?,?,?,?,?,?,?,?)",
                               [(r["tx"], r["log_index"], r["payer"], r["payee"], r["atomic"], *tail(r)) for r in rows[table]])
            db.executemany("insert into payments values (?,?,?,?,?,?,?,?,?,?,?)",
                           [(r["tx"], r["log_index"], r["payer"], r["payee"], r["via"], r["atomic"], r["scheme"], *tail(r))
                            for r in rows["payments"]])
            db.executemany("insert into removed values (?,?,?,?,?,?,?,?,?,?)",
                           [(r["tx"], r["log_index"], r["payer"], r["payee"], r["atomic"], r["reason"], *tail(r))
                            for r in rows["removed"]])
            db.execute("insert or replace into buckets values (?,?,?,?,?,1,?)",
                       (start, first, last, b["transfers"], int(b["atomic"]), json.dumps(meta, sort_keys=True)))
        log(f"{start} blocks {first}-{last}: {len(rows['w0'])} W0 transfers vs x402scan {b['transfers']}, "
            f"{time.time() - t0:.0f}s")
    return db
