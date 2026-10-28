"""AC-8: every out/examples/<rule>.csv holds 5 transaction hashes, and each returns a receipt with status 0x1."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ground_truth.rpc import Rpc  # noqa: E402


def main(folder=Path("out/examples")):
    rpc, bad = Rpc(cache_dir=Path("out/cache-examples")), []
    for path in sorted(folder.glob("W*.csv")):
        hashes = [r["tx"] for r in csv.DictReader(path.open())]
        receipts = rpc.batch([("eth_getTransactionReceipt", [h]) for h in hashes], cache=False, label=path.name)
        ok = [r["status"] == "0x1" for r in receipts]
        print(f"{path.stem}: {len(hashes)} hashes, {sum(ok)} with status 0x1")
        if len(hashes) != 5 or not all(ok):
            bad.append(path.stem)
    if bad:
        print("failed:", ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
