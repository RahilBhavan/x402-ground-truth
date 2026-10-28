import unittest

from ground_truth.x402scan_filter import collapse
from tests.fixtures import OTHER, PAYEE, PAYER, ROUTER


def leg(i, payer, payee, atomic):
    return {"tx": "t", "log_index": i, "payer": payer, "payee": payee, "atomic": atomic}


def short(rows):
    return [(r["log_index"], r["payer"], r["payee"], r["atomic"]) for r in rows]


class Collapse(unittest.TestCase):  # x402scan sync/transfers/trigger/lib/collapse.ts at the pinned commit
    def test_a_forward_becomes_one_row_with_the_amount_the_payee_received(self):  # Meridian keeps a 1% fee
        self.assertEqual(short(collapse([leg(1, PAYER, ROUTER, 1_000), leg(2, ROUTER, PAYEE, 990)])),
                         [(1, PAYER, PAYEE, 990)])

    def test_a_fan_out_follows_the_leg_closest_in_amount_and_keeps_the_fee(self):
        rows = collapse([leg(1, PAYER, ROUTER, 1_000), leg(2, ROUTER, OTHER, 10), leg(3, ROUTER, PAYEE, 990)])
        self.assertEqual(short(rows), [(1, PAYER, PAYEE, 990), (2, ROUTER, OTHER, 10)])

    def test_two_payouts_from_one_sender_with_nothing_coming_in_stay_two_rows(self):  # the 0x271f9fa7 split
        legs = [leg(1, ROUTER, OTHER, 1_040_000), leg(2, ROUTER, PAYEE, 6_960_000)]
        self.assertEqual(short(collapse(legs)), short(legs))

    def test_repeated_payments_between_the_same_pair_are_not_merged(self):
        legs = [leg(1, PAYER, PAYEE, 100), leg(2, PAYER, PAYEE, 200), leg(3, PAYER, PAYEE, 300)]
        self.assertEqual(short(collapse(legs)), short(legs))


if __name__ == "__main__":
    unittest.main()
