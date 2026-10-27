"""AC-4: W0 per x402scan bucket against x402scan's own figure for that bucket. W0 here is x402scan's filter exactly:
only addresses its syncer still reads (`synced = 1`)."""
import csv


def by_bucket(db):
    rows = db.execute("""select b.bucket_start, b.first_block, b.last_block, b.x402scan_transfers, b.x402scan_atomic,
                                count(w.tx), coalesce(sum(w.atomic), 0)
                         from buckets b left join w0 w on w.bucket_start = b.bucket_start and w.synced = 1
                         where b.done = 1 group by b.bucket_start order by b.bucket_start""").fetchall()
    return [{"bucket_start": s, "first_block": f, "last_block": l, "x402scan_transfers": xt, "w0_transfers": wt,
             "x402scan_usdc": xa / 1e6, "w0_usdc": wa / 1e6, "ratio_usdc": round(wa / xa, 4) if xa else None}
            for s, f, l, xt, xa, wt, wa in rows]


def write(rows, path, coverage_share):
    path.parent.mkdir(parents=True, exist_ok=True)
    total_x = sum(r["x402scan_usdc"] for r in rows)
    total_w = sum(r["w0_usdc"] for r in rows)
    corrected = total_w / (1 - coverage_share) if coverage_share < 1 else total_w
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["bucket_start"])
        w.writeheader()
        w.writerows(rows)
    return {"buckets": len(rows), "x402scan_usdc": round(total_x, 6), "w0_usdc": round(total_w, 6),
            "hour_coverage_correction_share": coverage_share, "w0_usdc_corrected": round(corrected, 6),
            "ratio_corrected": round(corrected / total_x, 4) if total_x else None}
