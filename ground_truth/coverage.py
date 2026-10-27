"""AC-5: what the log path misses. Scan every block in a range for transactions a facilitator sent, and bound the
count with each facilitator's nonce at the range edges."""
import json
from pathlib import Path

from .constants import PROXIES, TOPIC_AUTHORIZATION_USED, USDC

BLOCKS_PER_BATCH = 10


def scan(rpc, first, last, facilitators):
    """Sorted hashes of every transaction sent by a listed facilitator in [first, last]. Compact cache per batch,
    kept inside the RPC cache directory so an empty-cache rerun rescans."""
    cache = Path(rpc.cache_dir) / "scan"
    cache.mkdir(parents=True, exist_ok=True)
    found = []
    for a in range(first, last + 1, BLOCKS_PER_BATCH):
        b = min(a + BLOCKS_PER_BATCH - 1, last)
        path = cache / f"{a}-{b}.json"
        if path.exists():
            found += json.loads(path.read_text())
            continue
        blocks = rpc.batch([("eth_getBlockByNumber", [hex(n), True]) for n in range(a, b + 1)], cache=False,
                           label=f"blocks {a}-{b}")
        hits = sorted(t["hash"] for blk in blocks for t in blk["transactions"] if t["from"].lower() in facilitators)
        path.write_text(json.dumps(hits))
        found += hits
    return sorted(found)


def nonce_count(rpc, first, last, facilitators):
    """Transactions sent by all listed facilitators in [first, last], from nonces before and at the range."""
    addrs = sorted(facilitators)
    before = rpc.batch([("eth_getTransactionCount", [a, hex(first - 1)]) for a in addrs], label=f"nonces at {first - 1}")
    after = rpc.batch([("eth_getTransactionCount", [a, hex(last)]) for a in addrs], label=f"nonces at {last}")
    return sum(int(y, 16) - int(x, 16) for x, y in zip(before, after))


def has_marker(receipt):
    return any((l["address"].lower() == USDC and l["topics"][0] == TOPIC_AUTHORIZATION_USED)
               or l["address"].lower() in PROXIES.values() for l in receipt["logs"])


def crosscheck(scanned, log_path, missed_receipts, w0_atomic):
    """AC-5. A difference is a marker transaction the log path missed, or a log-path transaction the scan lacks.
    Missed transactions without a marker add their USDC transfers to the coverage correction."""
    from .settlements import _transfers
    missed_with_marker = sorted(r["transactionHash"] for r in missed_receipts if has_marker(r))
    not_in_scan = sorted(set(log_path) - set(scanned))
    missed_atomic = sum(t["atomic"] for r in missed_receipts if not has_marker(r) for t in _transfers(r["logs"]))
    total = w0_atomic + missed_atomic
    return {"facilitator_txs_by_block_scan": len(scanned), "facilitator_txs_on_log_path": len(log_path),
            "missed_txs": len(missed_receipts), "missed_with_marker": missed_with_marker,
            "log_path_not_in_scan": not_in_scan, "differences": len(missed_with_marker) + len(not_in_scan),
            "missed_w0_atomic": missed_atomic,
            "missed_share_of_w0_usdc": round(missed_atomic / total, 4) if total else 0.0}
