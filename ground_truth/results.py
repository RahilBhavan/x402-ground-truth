"""Slice 4: rules W2-W5 on the census, then the files the Results section cites.

Writes out/waterfall.json (every step, AC-7), out/sensitivity.csv (W3-W5 thresholds at 0.5x, 1x and 2x, AC-9) and
out/examples/<rule>.csv (5 transaction hashes per rule, AC-8). Return transfers for W3 are fetched once and stored in
the `returns` table, so a rerun makes no request.
"""
import csv
import json

from . import returns as return_query
from . import rules, waterfall
from .reconcile import summary as reconcile_summary

PAYMENT = ("tx", "log_index", "block", "payer", "payee", "atomic")
FACTORS = (0.5, 1, 2)


def payments(db):
    return [dict(zip(PAYMENT, r)) for r in db.execute(f"select {', '.join(PAYMENT)} from payments order by tx, log_index")]


def stored_returns(rpc, db, pays):
    db.execute(f"create table if not exists returns ({', '.join(PAYMENT)}, primary key (tx, log_index))")
    db.execute("create table if not exists returns_done (done int)")
    if not db.execute("select 1 from returns_done").fetchone():
        first, last = db.execute("select min(first_block), max(last_block) from buckets where done = 1").fetchone()
        after_w2 = {(p["payer"], p["payee"]) for p in pays if p["payer"] != p["payee"]}
        pairs = {(a, b) for a, b in after_w2 if not a.startswith("unknown") and not b.startswith("unknown")}
        found = return_query.fetch(rpc, pairs, first, last)
        with db:
            db.executemany(f"insert or replace into returns values ({', '.join('?' * len(PAYMENT))})",
                           [tuple(r[c] for c in PAYMENT) for r in found])
            db.execute("insert into returns_done values (1)")
    return [dict(zip(PAYMENT, r)) for r in db.execute(f"select {', '.join(PAYMENT)} from returns order by tx, log_index")]


def sensitivity(pays, rets):
    """Kept USDC with one threshold scaled at a time; the others stay at their defaults."""
    rows = []
    for name, default in rules.DEFAULTS.items():
        row = {"threshold": name, "default": default}
        for f in FACTORS:
            _, kept = rules.apply(pays, rets, **{name: default * f})
            row[f"kept_usdc_{f}x"] = round(sum(p["atomic"] for p in kept) / 1e6, 6)
        rows.append(row)
    return rows


def examples(db, steps):
    """5 removed transactions per rule, evenly spaced through the removed rows in (tx, log index) order."""
    pick = lambda rows: [rows[i * len(rows) // 5] for i in range(5)] if len(rows) >= 5 else rows
    w1 = [dict(zip(("tx", "log_index", "block", "atomic", "reason"), r)) for r in
          db.execute("select tx, log_index, block, atomic, reason from removed order by tx, log_index")]
    out = {"W1": pick(w1)}
    for rule, _, removed in steps:
        out[rule] = pick(sorted(removed, key=rules.key))
    return out


def write(db, rpc, out, x402scan_commit, contracts_commit):
    pays = payments(db)
    rets = stored_returns(rpc, db, pays)
    steps, kept = rules.apply(pays, rets)
    w = waterfall.build(db, x402scan_commit, contracts_commit, later_rules=steps)
    summary = reconcile_summary(db, out)
    kept_atomic = sum(p["atomic"] for p in kept)
    w.update(reconcile=summary, returns_found=len(rets), kept={"count": len(kept), "atomic": kept_atomic},
             thresholds=rules.DEFAULTS)
    (out / "waterfall.json").write_text(json.dumps(w, indent=1, sort_keys=True))
    sens = sensitivity(pays, rets)
    with (out / "sensitivity.csv").open("w", newline="") as f:
        c = csv.DictWriter(f, fieldnames=list(sens[0]))
        c.writeheader()
        c.writerows(sens)
    (out / "examples").mkdir(parents=True, exist_ok=True)
    for rule, rows in examples(db, steps).items():
        with (out / "examples" / f"{rule}.csv").open("w", newline="") as f:
            c = csv.DictWriter(f, fieldnames=["tx", "block", "atomic"], extrasaction="ignore")
            c.writeheader()
            c.writerows(rows)
    return w
