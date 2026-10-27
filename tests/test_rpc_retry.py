import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ground_truth.rpc import Rpc, RpcError
from tests.fake_rpc import FakeRpc, Rate

ROOT = Path(__file__).resolve().parent.parent


def always_429(method, params):
    raise Rate()


class RetryAndResume(unittest.TestCase):  # AC-14
    def test_cli_exits_3_after_5_tries_when_the_rpc_always_rate_limits(self):
        fake = FakeRpc(always_429)
        self.addCleanup(fake.close)
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "GROUND_TRUTH_RPC": fake.url, "GROUND_TRUTH_RPC_PAUSE": "0"}
            r = subprocess.run([sys.executable, "-m", "ground_truth", "hour", "--out", f"{tmp}/o", "--cache", f"{tmp}/c"],
                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("after 5 tries", r.stderr)
        self.assertEqual(len(fake.requests), 5)

    def test_rerun_after_recovery_fetches_no_cached_chunk(self):
        healthy = {"on": True}

        def answer(method, params):
            if params[0]["fromBlock"] == "0x2" and not healthy["on"]:
                raise Rate()
            return [{"block": params[0]["fromBlock"]}]

        fake = FakeRpc(answer)
        self.addCleanup(fake.close)
        chunk = lambda b: [("eth_getLogs", [{"fromBlock": b, "toBlock": b}])]
        with tempfile.TemporaryDirectory() as tmp:
            first = Rpc(fake.url, Path(tmp), pause=0)
            first.batch(chunk("0x1"))
            healthy["on"] = False
            with self.assertRaises(RpcError):
                first.batch(chunk("0x2"))
            before = len(fake.requests)
            healthy["on"] = True
            second = Rpc(fake.url, Path(tmp), pause=0)
            self.assertEqual(second.batch(chunk("0x1")), [[{"block": "0x1"}]])
            self.assertEqual(len(fake.requests), before)  # chunk 1 came from the cache
            second.batch(chunk("0x2"))
            self.assertEqual(len(fake.requests), before + 1)


class Pool(unittest.TestCase):
    def test_lookups_rotate_through_the_pool_and_logs_stay_on_the_first_node(self):
        first, second = FakeRpc(lambda m, p: [] if m == "eth_getLogs" else {"n": 1}), FakeRpc(lambda m, p: {"n": 2})
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        with tempfile.TemporaryDirectory() as tmp:
            rpc = Rpc([first.url, second.url], Path(tmp), pause=0)
            for i in range(4):
                rpc.call("eth_getTransactionReceipt", [hex(i)])
                rpc.call("eth_getLogs", [{"fromBlock": hex(i)}])
        self.assertEqual((len(first.requests), len(second.requests)), (6, 2))
        self.assertTrue(all(r[0]["method"] == "eth_getTransactionReceipt" for r in second.requests))


if __name__ == "__main__":
    unittest.main()
