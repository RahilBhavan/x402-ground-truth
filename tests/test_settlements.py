import unittest

from ground_truth.settlements import classify
from tests.fixtures import (FAC, FACILITATORS, OTHER, PAYEE, PAYER, PROXIES, ROUTER, auth_used, claimed, proxy_settled,
                            receipt, transfer)


def run(logs, sender=FAC, channels=None):
    return classify(receipt(logs), sender, FACILITATORS, channels or {})


class Classify(unittest.TestCase):
    def test_transaction_not_sent_by_a_facilitator_is_outside_w0(self):
        self.assertIsNone(run([auth_used(0, PAYER), transfer(1, PAYER, PAYEE, 10_000)], sender=OTHER))

    def test_three_authorizations_in_one_transaction_are_three_payments(self):  # AC-10
        logs = [auth_used(0, PAYER), transfer(1, PAYER, PAYEE, 100), auth_used(2, PAYER), transfer(3, PAYER, PAYEE, 200),
                auth_used(4, PAYER), transfer(5, PAYER, PAYEE, 300)]
        out = run(logs)
        self.assertEqual([p["atomic"] for p in out["payments"]], [100, 200, 300])
        self.assertEqual(len(out["w0"]), 3)

    def test_upto_proxy_settled_transfer_passes_w1(self):  # AC-10
        out = run([transfer(0, PAYER, PAYEE, 5_000), proxy_settled(1, "upto")])
        self.assertEqual([(p["scheme"], p["payer"], p["atomic"]) for p in out["payments"]], [("upto", PAYER, 5_000)])

    def test_routed_second_hop_is_removed_and_counted_once(self):  # W1, slice 1 finding 1
        out = run([auth_used(0, PAYER), transfer(1, PAYER, ROUTER, 1_000), transfer(2, ROUTER, PAYEE, 1_000)])
        self.assertEqual([(p["payer"], p["payee"]) for p in out["payments"]], [(PAYER, ROUTER)])
        self.assertEqual([r["reason"] for r in out["removed"]], ["second_hop"])

    def test_forward_of_most_of_a_payment_is_a_second_hop(self):  # slice 1 finding 2: 99% forwarded
        out = run([auth_used(0, PAYER), transfer(1, PAYER, ROUTER, 30_906_598), transfer(2, ROUTER, PAYEE, 30_597_533)])
        self.assertEqual([r["reason"] for r in out["removed"]], ["second_hop"])

    def test_unmarked_transfer_in_facilitator_transaction_is_a_non_payment(self):  # W1
        out = run([transfer(0, OTHER, PAYEE, 7_000)])
        self.assertEqual(out["payments"], [])
        self.assertEqual([r["reason"] for r in out["removed"]], ["non_payment"])
        self.assertEqual(len(out["w0"]), 1)

    def test_batch_claim_is_a_payment_and_its_payout_is_a_channel_movement(self):  # slice 1 finding 3
        channels = {"0x" + "c1" * 32: {"payer": PAYER, "receiver": PAYEE}}
        out = run([claimed(0, "c1", 4_000), transfer(1, PROXIES["batch_settlement"], PAYEE, 4_000)], channels=channels)
        self.assertEqual([(p["scheme"], p["payer"], p["payee"], p["atomic"]) for p in out["payments"]],
                         [("batch_settlement", PAYER, PAYEE, 4_000)])
        self.assertEqual([r["reason"] for r in out["removed"]], ["channel_movement"])

    def test_batch_claim_for_unknown_channel_keeps_amount_and_marks_parties_unknown(self):
        out = run([claimed(0, "c2", 9)])
        self.assertEqual((out["payments"][0]["payer"], out["payments"][0]["atomic"]), ("unknown", 9))


if __name__ == "__main__":
    unittest.main()
