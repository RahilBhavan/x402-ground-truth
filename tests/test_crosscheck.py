import tempfile
import unittest
from pathlib import Path

from ground_truth import channels
from ground_truth.coverage import crosscheck
from ground_truth.rpc import Rpc
from tests.fake_rpc import FakeRpc
from tests.fixtures import PAYER, PAYEE, auth_used, receipt, transfer

A, B, C = ("0x" + c * 64 for c in "abc")


class Crosscheck(unittest.TestCase):  # AC-5
    def test_missed_transaction_with_a_marker_is_a_difference(self):
        missed = [receipt([auth_used(0, PAYER), transfer(1, PAYER, PAYEE, 50)], h=C)]
        out = crosscheck(scanned=[A, B, C], log_path=[A, B], missed_receipts=missed, w0_atomic=1_000)
        self.assertEqual(out["differences"], 1)
        self.assertEqual(out["missed_with_marker"], [C])

    def test_missed_transaction_without_marker_adds_its_transfers_to_the_correction(self):
        missed = [receipt([transfer(0, PAYER, PAYEE, 250)], h=C)]
        out = crosscheck(scanned=[A, B, C], log_path=[A, B], missed_receipts=missed, w0_atomic=750)
        self.assertEqual((out["differences"], out["missed_w0_atomic"], out["missed_share_of_w0_usdc"]), (0, 250, 0.25))

    def test_log_path_transaction_absent_from_scan_is_a_difference(self):
        out = crosscheck(scanned=[A], log_path=[A, B], missed_receipts=[], w0_atomic=0)
        self.assertEqual((out["differences"], out["log_path_not_in_scan"]), (1, [B]))


class ChannelLookup(unittest.TestCase):
    def test_walks_back_in_50k_spans_until_every_channel_is_found(self):
        cid = "0x" + "c1" * 32
        data = "0x" + "00" * 12 + PAYER[2:] + "00" * 32 + "00" * 12 + PAYEE[2:] + "00" * 32 * 4

        def answer(method, params):
            f = params[0]
            return [{"topics": [f["topics"][0], cid], "data": data}] if int(f["toBlock"], 16) < 100_000 else []

        fake = FakeRpc(answer)
        self.addCleanup(fake.close)
        with tempfile.TemporaryDirectory() as tmp:
            found = channels.lookup(Rpc(fake.url, Path(tmp), pause=0), {cid}, 149_999)
        self.assertEqual(found, {cid: {"payer": PAYER, "receiver": PAYEE}})
        spans = [(int(r[0]["params"][0]["fromBlock"], 16), int(r[0]["params"][0]["toBlock"], 16)) for r in fake.requests]
        self.assertEqual(spans, [(100_000, 149_999), (50_000, 99_999)])

    def test_a_refused_old_range_ends_the_walk_instead_of_failing(self):
        from tests.fake_rpc import Rate

        def answer(method, params):
            if int(params[0]["toBlock"], 16) < 100_000:
                raise Rate()  # the fake's refusal stands in for the node's HTTP 403 on old ranges
            return []

        fake = FakeRpc(answer)
        self.addCleanup(fake.close)
        with tempfile.TemporaryDirectory() as tmp:
            found = channels.lookup(Rpc(fake.url, Path(tmp), pause=0, tries=1), {"0x" + "c9" * 32}, 149_999)
        self.assertEqual(found, {})


if __name__ == "__main__":
    unittest.main()
