"""Slice 1 and 2: W0/W1 and coverage for one hour of Base blocks, keyless."""
import calendar
import json
import time

from . import coverage, facilitators
from .constants import DUST_ATOMIC, USDC, X402_CONTRACTS_COMMIT, X402SCAN_COMMIT
from .pipeline import batched, collect
from .settlements import REASONS


def block_at(rpc, ts):
    """First block with timestamp >= ts, by binary search around a 2-second-block estimate."""
    ts_of = lambda n: int(rpc.call("eth_getBlockByNumber", [hex(n), False], label=f"block {n}")["timestamp"], 16)
    head = rpc.call("eth_getBlockByNumber", ["latest", False], cache=False, label="latest block")
    guess = int(head["number"], 16) - (int(head["timestamp"], 16) - ts) // 2
    lo, hi = guess - 2000, guess + 2000
    if not ts_of(lo) < ts <= ts_of(hi):
        raise RuntimeError(f"block estimate for {ts} is off by more than 2,000 blocks")
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if ts_of(mid) < ts else (lo, mid)
    return hi


def usdc(rows):
    return {"count": len(rows), "usdc": sum(r["atomic"] for r in rows) / 1e6}


def summarize(rows):
    pays = rows["payments"]
    group = lambda key: {k: usdc([p for p in pays if p[key] == k]) for k in sorted({p[key] for p in pays})}
    return {
        "w0": usdc(rows["w0"]),
        "w1_removed": {k: usdc([r for r in rows["removed"] if r["reason"] == k]) for k in REASONS},
        "w1_added_batch_claims": usdc([p for p in pays if p["scheme"] == "batch_settlement"]),
        "w1": usdc(pays),
        "dust_under_1_cent": {**usdc([p for p in pays if p["atomic"] < DUST_ATOMIC]),
                              "share_of_payments": round(sum(p["atomic"] < DUST_ATOMIC for p in pays) / max(len(pays), 1), 4)},
        "by_scheme": group("scheme"), "by_facilitator": group("facilitator"),
    }


def run(rpc, start_iso, scan=True):
    start = calendar.timegm(time.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ"))
    first, last = block_at(rpc, start), block_at(rpc, start + 3600) - 1
    fac = facilitators.load()
    decimals = int(rpc.call("eth_call", [{"to": USDC, "data": "0x313ce567"}, "latest"], label="USDC decimals()"), 16)
    if decimals != 6:
        raise RuntimeError(f"USDC decimals() returned {decimals}, expected 6")
    rows, fac_hashes, meta = collect(rpc, first, last, fac)
    result = {"hour_start_utc": start_iso, "first_block": first, "last_block": last,
              "x402scan_commit": X402SCAN_COMMIT, "x402_contracts_commit": X402_CONTRACTS_COMMIT,
              **meta, **summarize(rows),
              "check_by_hand": [p["tx"] for p in rows["payments"][:: max(len(rows["payments"]) // 5, 1)][:5]]}
    if scan:
        result["coverage"] = hour_coverage(rpc, first, last, fac, fac_hashes, sum(r["atomic"] for r in rows["w0"]))
    return result, rows


def hour_coverage(rpc, first, last, fac, fac_hashes, w0_atomic):
    scanned = coverage.scan(rpc, first, last, fac)
    missed = sorted(set(scanned) - set(fac_hashes))
    out = coverage.crosscheck(scanned, fac_hashes, batched(rpc, "eth_getTransactionReceipt", missed), w0_atomic)
    return {**out, "facilitator_txs_by_nonce": coverage.nonce_count(rpc, first, last, fac)}


def write(result, rows, out_dir, coverage_path=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hour.json").write_text(json.dumps(result, indent=1, sort_keys=True))
    for k in ("payments", "removed"):
        (out_dir / f"hour-{k}.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows[k]))
    if coverage_path and "coverage" in result:
        coverage_path.parent.mkdir(parents=True, exist_ok=True)
        coverage_path.write_text(json.dumps({"hour_start_utc": result["hour_start_utc"], "first_block": result["first_block"],
                                             "last_block": result["last_block"], **result["coverage"]}, indent=1, sort_keys=True))
