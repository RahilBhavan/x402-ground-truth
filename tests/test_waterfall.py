import sqlite3
import unittest

from ground_truth import census, results, rules, waterfall
from tests.fixtures import OTHER, PAYEE, PAYER, ROUTER

PAYERS = [PAYER, OTHER, ROUTER, "0x" + "5" * 40]


def db_with(payments):
    db = sqlite3.connect(":memory:")
    db.executescript(census.SCHEMA)
    db.execute("insert into buckets values ('b', 100, 200, 0, 0, 1, '{}')")
    for i, (payer, payee, atomic) in enumerate(payments):
        row = (f"0x{i:064x}", 0, 150, payer, payee, atomic, "f", "s", 1, "b")
        for table in ("transfers", "w0"):
            db.execute(f"insert into {table} values (?,?,?,?,?,?,?,?,?,?)", row)
        db.execute("insert into payments values (?,?,?,?,?,?,?,?,?,?,?,?)", row[:6] + (None, "eip3009") + row[6:])
    return db


class Waterfall(unittest.TestCase):  # AC-7
    def test_every_rule_step_removes_from_the_previous_remainder_and_reports_its_dust(self):
        db = db_with([(PAYEE, PAYEE, 5_000)] + [(p, PAYEE, 20_000) for p in PAYERS] + [(PAYER, OTHER, 7)])
        steps, kept = rules.apply(results.payments(db), [])
        w = waterfall.build(db, "c", "d", later_rules=steps)
        for prev, step in zip(w["steps"], w["steps"][1:]):
            self.assertEqual(step["remaining_atomic"], prev["remaining_atomic"] - step["removed_atomic"] + step["added_atomic"])
            self.assertEqual(step["remaining_count"], prev["remaining_count"] - step["removed_count"] + step["added_count"])
        by_rule = {s["rule"]: s for s in w["steps"] if s["rule"] in ("W2", "W4")}
        self.assertEqual((by_rule["W2"]["removed_atomic"], by_rule["W2"]["dust_removed_count"]), (5_000, 1))
        self.assertEqual((by_rule["W4"]["removed_atomic"], by_rule["W4"]["dust_removed_atomic"]), (7, 7))
        self.assertEqual(w["steps"][-1]["remaining_atomic"], sum(p["atomic"] for p in kept))
        self.assertEqual(set(w["rule_versions"]), {"W0", "W1", "W2", "W3", "W4", "W5"})

    def test_sensitivity_scales_one_threshold_at_a_time(self):  # AC-9
        db = db_with([(p, PAYEE, 20_000) for p in PAYERS])
        rows = results.sensitivity(results.payments(db), [])
        self.assertEqual([r["threshold"] for r in rows], list(rules.DEFAULTS))
        w4 = next(r for r in rows if r["threshold"] == "w4_payments")
        self.assertEqual((w4["kept_usdc_1x"], w4["kept_usdc_2x"]), (0.08, 0.0))  # 4 payments pass 3, fail 6


if __name__ == "__main__":
    unittest.main()
