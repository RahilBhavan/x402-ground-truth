import argparse
import json
import sys
from pathlib import Path

from . import capture, census, facilitators, hour, results
from .returns import NotReady
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
    r = sub.add_parser("run", help="census of the complete x402scan buckets, reconciliation, rules W1-W5 and waterfall")
    r.add_argument("--buckets", required=True, help="out/reconcile/x402scan-buckets-*.json")
    r.add_argument("--db", default="out/settlements.sqlite")
    r.add_argument("--cache", default="out/cache")
    a = ap.parse_args()
    if a.cmd == "run":
        rpc = Rpc(cache_dir=Path(a.cache))
        try:
            db = census.run(rpc, a.buckets, a.db, facilitators.load(), log=lambda m: print(m, flush=True))
            w = results.write(db, rpc, Path(a.db).parent, X402SCAN_COMMIT, X402_CONTRACTS_COMMIT)
        except RpcError as e:
            print(e, file=sys.stderr)
            sys.exit(3)
        except NotReady as e:  # the census is kept; rerun once the chain has 24 hours past the window
            print(e, file=sys.stderr)
            sys.exit(4)
        print(json.dumps({"reconcile": w["reconcile"], "kept": w["kept"]}, indent=1))
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
