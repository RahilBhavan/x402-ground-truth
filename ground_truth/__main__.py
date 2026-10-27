import argparse
import json
import sys
from pathlib import Path

from . import capture, census, facilitators, hour, reconcile, waterfall
from .constants import X402_CONTRACTS_COMMIT, X402SCAN_COMMIT
from .rpc import Rpc, RpcError


def main():
    ap = argparse.ArgumentParser(prog="python -m ground_truth")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture", help="save x402scan's rolling Base figure")
    c.add_argument("--days", type=int, default=7)
    h = sub.add_parser("hour", help="slice 1: one hour of Base blocks")
    h.add_argument("--start", default="2026-10-25T14:00:00Z")
    h.add_argument("--out", default="out/s1")
    h.add_argument("--cache", default="out/cache")
    h.add_argument("--no-scan", action="store_true", help="skip the block-by-block coverage scan")
    k = sub.add_parser("run", help="slice 3: census of the complete x402scan buckets, reconciliation and waterfall")
    k.add_argument("--buckets", required=True, help="out/reconcile/x402scan-buckets-*.json")
    k.add_argument("--db", default="out/settlements.sqlite")
    k.add_argument("--cache", default="out/cache")
    a = ap.parse_args()
    if a.cmd == "run":
        try:
            db = census.run(Rpc(cache_dir=Path(a.cache)), a.buckets, a.db, facilitators.load(),
                            log=lambda m: print(m, flush=True))
        except RpcError as e:
            print(e, file=sys.stderr)
            sys.exit(3)
        out = Path(a.db).parent
        share = json.loads((out / "reconcile/hour-coverage.json").read_text())["missed_share_of_w0_usdc"]
        summary = reconcile.write(reconcile.by_bucket(db), out / "reconcile/x402scan.csv", share)
        w = waterfall.build(db, X402SCAN_COMMIT, X402_CONTRACTS_COMMIT)
        (out / "waterfall.json").write_text(json.dumps({**w, "reconcile": summary}, indent=1, sort_keys=True))
        print(json.dumps(summary, indent=1))
        return
    if a.cmd == "capture":
        path, rec = capture.capture(a.days)
        print(f"{path}: {rec['stats']['total_transactions']:,} tx, ${rec['usdc']:,.2f} ({a.days}d, base)")
    else:
        try:
            result, rows = hour.run(Rpc(cache_dir=Path(a.cache)), a.start, scan=not a.no_scan)
        except RpcError as e:
            print(e, file=sys.stderr)
            sys.exit(3)
        hour.write(result, rows, Path(a.out), Path(a.out).parent / "reconcile" / "hour-coverage.json")
        print(json.dumps({k: result.get(k) for k in ("first_block", "last_block", "w0", "w1_removed", "w1", "coverage")}, indent=1))


if __name__ == "__main__":
    main()
