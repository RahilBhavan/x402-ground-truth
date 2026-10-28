import tempfile
import unittest
from pathlib import Path

from ground_truth import returns
from ground_truth.constants import TOPIC_TRANSFER, USDC
from ground_truth.rpc import Rpc
from tests.fake_rpc import FakeRpc
from tests.fixtures import OTHER, PAYEE, PAYER, topic


def log(frm, to, block, amount, i=0):
    return {"address": USDC, "topics": [TOPIC_TRANSFER, topic(frm), topic(to)], "data": hex(amount),
            "blockNumber": hex(block), "logIndex": hex(i), "transactionHash": "0x" + f"{block:064x}"}


class Returns(unittest.TestCase):
    def fake(self, head):
        seen = []

        def answer(method, params):
            if method == "eth_blockNumber":
                return hex(head)
            seen.append(params[0])
            # the node returns the cross product: PAYEE -> OTHER is not a real pair and must be dropped
            return [log(PAYEE, PAYER, 150, 900), log(PAYEE, OTHER, 160, 900, 1)] if int(params[0]["fromBlock"], 16) == 100 else []

        fake = FakeRpc(answer)
        self.addCleanup(fake.close)
        return Rpc(fake.url, Path(self.enterContext(tempfile.TemporaryDirectory())), pause=0), seen

    def test_keeps_only_transfers_back_along_a_real_pair_up_to_24_hours_after_the_window(self):
        rpc, seen = self.fake(head=10 ** 7)
        out = returns.fetch(rpc, {(PAYER, PAYEE), (OTHER, PAYER)}, 100, 200)
        self.assertEqual([(r["payer"], r["payee"], r["atomic"]) for r in out], [(PAYEE, PAYER, 900)])
        self.assertEqual(max(int(f["toBlock"], 16) for f in seen), 200 + 43_200)
        self.assertTrue(all(f["topics"][0] == TOPIC_TRANSFER for f in seen))

    def test_refuses_to_run_before_the_chain_has_24_hours_past_the_window(self):
        rpc, seen = self.fake(head=200 + 43_199)
        with self.assertRaises(returns.NotReady):
            returns.fetch(rpc, {(PAYER, PAYEE)}, 100, 200)
        self.assertEqual(seen, [])

    def test_groups_respect_both_limits(self):
        pairs = {(f"0x{p:040x}", f"0x{e:040x}") for e in range(5) for p in range(e * 3, e * 3 + 3)}
        old = returns.GROUP, returns.MAX_PAYERS
        self.addCleanup(lambda: setattr(returns, "GROUP", old[0]) or setattr(returns, "MAX_PAYERS", old[1]))
        returns.GROUP, returns.MAX_PAYERS = 2, 4
        gs = returns.groups(pairs)
        self.assertTrue(all(len(e) <= 2 and len(p) <= 4 for e, p in gs))
        covered = {(p, e) for es, ps in gs for e in es for p in ps}
        self.assertTrue(pairs <= covered)


if __name__ == "__main__":
    unittest.main()
