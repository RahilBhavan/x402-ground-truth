"""AC-4: W0 per x402scan bucket against x402scan's own figure for that bucket.

W0 here is x402scan's filter exactly: only addresses its syncer still reads (`synced = 1`), collapsed as it collapses.
The census finds facilitator transactions with no x402 marker itself, so the hour cross-check (AC-5) is reported
beside the ratio as a coverage check, not applied as a correction.
"""
import csv
import json


def by_bucket(db):
    rows = db.execute("""select b.bucket_start, b.first_block, b.last_block, b.x402scan_transfers, b.x402scan_atomic,
                                count(w.tx), coalesce(sum(w.atomic), 0)
                         from buckets b left join w0 w on w.bucket_start = b.bucket_start and w.synced = 1
                         where b.done = 1 group by b.bucket_start order by b.bucket_start""").fetchall()
    return [{"bucket_start": s, "first_block": f, "last_block": l, "x402scan_transfers": xt, "w0_transfers": wt,
             "ratio_transfers": round(wt / xt, 4) if xt else None,
             "x402scan_usdc": xa / 1e6, "w0_usdc": wa / 1e6, "ratio_usdc": round(wa / xa, 4) if xa else None}
            for s, f, l, xt, xa, wt, wa in rows]


def write(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["bucket_start"])
        w.writeheader()
        w.writerows(rows)
    total = lambda k: sum(r[k] for r in rows)
    x, w0 = total("x402scan_usdc"), total("w0_usdc")
    return {"buckets": len(rows), "x402scan_transfers": total("x402scan_transfers"), "w0_transfers": total("w0_transfers"),
            "x402scan_usdc": round(x, 6), "w0_usdc": round(w0, 6), "ratio_usdc": round(w0 / x, 4) if x else None}


def hour_check(path):
    """AC-5's hour cross-check, if slice 2's `hour` command has written it."""
    if not path.exists():
        return "not run"
    c = json.loads(path.read_text())
    return {k: c[k] for k in ("differences", "missed_with_marker", "log_path_not_in_scan")}


def summary(db, out):
    """Write out/reconcile/x402scan.csv; return the reconciliation summary for out/waterfall.json."""
    return {**write(by_bucket(db), out / "reconcile/x402scan.csv"),
            "hour_coverage_check": hour_check(out / "reconcile/hour-coverage.json")}
