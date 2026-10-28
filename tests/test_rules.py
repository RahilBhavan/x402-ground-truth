import unittest

from ground_truth import rules
from tests.fixtures import OTHER, PAYEE, PAYER, ROUTER


def pay(i, payer=PAYER, payee=PAYEE, atomic=1_000, block=100):
    return {"tx": f"0x{i:064x}", "log_index": 0, "block": block, "payer": payer, "payee": payee, "atomic": atomic}


def back(i, atomic, block, frm=PAYEE, to=PAYER):
    return {"tx": f"0x{i + 900:064x}", "log_index": 1, "block": block, "payer": frm, "payee": to, "atomic": atomic}


class Rules(unittest.TestCase):  # AC-6: each rule removes at least one fixture payment and keeps another
    def test_w1_is_the_attribution_classifier(self):
        self.assertIs(rules.w1.__name__, "classify")

    def test_w2_removes_a_self_payment(self):
        self_pay, real = pay(1, payer=PAYEE), pay(2)
        self.assertEqual(rules.w2([self_pay, real]), [self_pay])

    def test_w3_removes_a_payment_sent_back_within_24_hours(self):
        refunded, kept, late = pay(1, block=100), pay(2, block=100), pay(3, block=100)
        returns = [back(1, 950, 200), back(2, 500, 300), back(3, 1_000, 100 + rules.DAY_BLOCKS + 1)]
        self.assertEqual(rules.w3([refunded], returns), [refunded])
        self.assertEqual(rules.w3([kept, late], returns[1:]), [])

    def test_w3_matches_each_return_once_and_never_before_the_payment(self):
        a, b = pay(1, block=100), pay(2, block=101)
        self.assertEqual(rules.w3([a, b], [back(1, 1_000, 102)]), [a])
        self.assertEqual(rules.w3([b], [back(1, 1_000, 100)]), [])

    def test_w4_removes_a_payee_with_too_few_payments_or_payers(self):
        busy = [pay(i, payer=p) for i, p in enumerate([PAYER, OTHER, ROUTER])]
        one_payer = [pay(10 + i, payee=OTHER) for i in range(5)]
        self.assertEqual(rules.w4(busy + one_payer), one_payer)

    def test_w5_removes_a_pair_with_a_thousand_identical_payments_in_one_day(self):
        burst = [pay(i, block=1_000 + i) for i in range(1_000)]
        varied = [pay(2_000 + i, payee=OTHER, atomic=1_000 + i) for i in range(1_000)]
        self.assertEqual(rules.w5(burst + varied), burst)

    def test_w5_splits_at_the_utc_day_boundary(self):
        midnight = next(b for b in range(10 ** 6) if rules.utc_day(b) != rules.utc_day(0))
        straddle = [pay(i, block=midnight - 500 + i) for i in range(1_000)]
        self.assertEqual(rules.w5(straddle), [])

    def test_apply_runs_the_rules_in_order_on_survivors(self):
        self_pay = pay(1, payer=PAYEE)
        busy = [pay(10 + i, payer=p) for i, p in enumerate([PAYER, OTHER, ROUTER])]
        steps, kept = rules.apply([self_pay] + busy, [])
        self.assertEqual([(r, len(out)) for r, _, out in steps], [("W2", 1), ("W3", 0), ("W4", 0), ("W5", 0)])
        self.assertEqual(kept, busy)

    def test_thresholds_change_the_result(self):  # AC-9's mechanism
        payments = [pay(i, payer=p) for i, p in enumerate([PAYER, OTHER, ROUTER, "0x" + "5" * 40])]  # W4 keeps 3 of 4
        returns = [back(0, 500, 200)]  # half of PAYER's payment comes back
        self.assertEqual(rules.apply(payments, returns)[1], payments)
        self.assertEqual(rules.apply(payments, returns, w3_share=0.45)[1], payments[1:])


if __name__ == "__main__":
    unittest.main()
