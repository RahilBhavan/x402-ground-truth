"""The waterfall: W0, then each rule's removals (and batch claims added by W1), with every input pinned.

W0 rows are x402scan's collapsed rows; W1 works on every USDC leg. The step "pass-through legs x402scan merged"
adds back the legs and amounts the collapse folded, so every step adds up and W1's removals are shown in full."""
from .settlements import REASONS

RULE_VERSIONS = {"W0": "x402scan-filter-3", "W1": "settlements-3"}


def build(db, x402scan_commit, contracts_commit, later_rules=()):
    first, last = db.execute("select min(first_block), max(last_block) from buckets where done = 1").fetchone()
    count, atomic = db.execute("select count(*), coalesce(sum(atomic), 0) from w0 where synced = 1").fetchone()
    steps = [{"rule": "W0", "label": "x402scan's filter", "removed_count": 0, "removed_atomic": 0, "added_count": 0,
              "added_atomic": 0, "remaining_count": count, "remaining_atomic": atomic}]

    def step(rule, label, removed=(0, 0), added=(0, 0)):
        prev = steps[-1]
        steps.append({"rule": rule, "label": label, "removed_count": removed[0], "removed_atomic": removed[1],
                      "added_count": added[0], "added_atomic": added[1],
                      "remaining_count": prev["remaining_count"] - removed[0] + added[0],
                      "remaining_atomic": prev["remaining_atomic"] - removed[1] + added[1]})

    step("W0", "listed addresses x402scan no longer syncs",
         added=db.execute("select count(*), coalesce(sum(atomic), 0) from w0 where synced = 0").fetchone())
    legs = db.execute("select count(*), coalesce(sum(atomic), 0) from transfers").fetchone()
    rows = db.execute("select count(*), coalesce(sum(atomic), 0) from w0").fetchone()
    step("W1", "pass-through legs x402scan merged", added=(legs[0] - rows[0], legs[1] - rows[1]))
    for reason in REASONS:
        step("W1", reason.replace("_", " "),
             removed=db.execute("select count(*), coalesce(sum(atomic), 0) from removed where reason = ?", (reason,)).fetchone())
    step("W1", "batch claims", added=db.execute(
        "select count(*), coalesce(sum(atomic), 0) from payments where scheme = 'batch_settlement'").fetchone())
    for rule, label, removed in later_rules:
        step(rule, label, removed=removed)
    w1 = db.execute("select count(*), coalesce(sum(atomic), 0) from payments").fetchone()
    return {"first_block": first, "last_block": last, "x402scan_commit": x402scan_commit,
            "x402_contracts_commit": contracts_commit, "rule_versions": dict(RULE_VERSIONS),
            "steps": steps, "w1_payments_check": {"count": w1[0], "atomic": w1[1]}}
