import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ground_truth import census, reconcile, waterfall
from ground_truth.constants import TOPIC_AUTHORIZATION_USED
from ground_truth.rpc import Rpc
from tests.fake_rpc import FakeRpc
from tests.fixtures import FAC, FACILITATORS, OTHER, PAYEE, PAYER, auth_used, receipt, transfer

T0 = 1_000_000  # bucket starts; the fake chain has block n at timestamp 2n
MARKED, UNMARKED = T0 // 2, T0 // 2 + 100  # the facilitator's two transactions in bucket 1
UH = "0x" + "22" * 32


def chain(method, params):
    if method == "eth_getBlockByNumber":
        n = 10 ** 7 if params[0] == "latest" else int(params[0], 16)
        txs = [{"hash": UH, "from": FAC}, {"hash": "0x" + "33" * 32, "from": PAYER}] if n == UNMARKED else []
        return {"number": hex(n), "timestamp": hex(2 * n), "transactions": txs if params[1] else []}
    if method == "eth_getTransactionCount":
        assert params[0] == FAC, params
        return hex(sum(b <= int(params[1], 16) for b in (MARKED, UNMARKED)))
    if method == "eth_getLogs":
        f = params[0]
        first = int(f["fromBlock"], 16)
        if f.get("topics") == [TOPIC_AUTHORIZATION_USED] and first == T0 // 2:  # one payment in bucket 1 only
            return [{**auth_used(0, PAYER), "transactionHash": "0x" + "11" * 32, "blockNumber": hex(MARKED)}]
        return []
    if method == "eth_getTransactionByHash":
        return {"hash": params[0], "from": FAC, "input": "0x"}
    if method == "eth_getTransactionReceipt" and params[0] == UH:  # moves USDC with no x402 marker
        return receipt([transfer(0, OTHER, PAYEE, 7_000)], h=UH)
    if method == "eth_getTransactionReceipt":
        return receipt([auth_used(0, PAYER), transfer(1, PAYER, PAYEE, 2_500_000)], h=params[0])
    raise AssertionError(method)


def capture(path):
    rows = [{"bucket_start": "x", "total_transactions": 0, "total_amount": 0}]
    for i in range(2):
        start = T0 + 12_600 * i
        rows.append({"bucket_start": census.iso(start) + ".000Z", "total_transactions": 2 * (1 - i),
                     "total_amount": 2_507_000 * (1 - i)})
    rows.append({"bucket_start": "y", "total_transactions": 0, "total_amount": 0})
    path.write_text(json.dumps({"bucketed": {"data": rows}}))


class Census(unittest.TestCase):
    def setUp(self):
        self.fake = FakeRpc(chain)
        self.addCleanup(self.fake.close)
        self.tmp = Path(tempfile.mkdtemp(dir=Path.home() / "scratch"))
        capture(self.tmp / "buckets.json")

    def run_census(self):
        rpc = Rpc(self.fake.url, self.tmp / "cache", pause=0)
        return census.run(rpc, self.tmp / "buckets.json", self.tmp / "s.sqlite", FACILITATORS, log=lambda m: None)

    def test_drops_partial_first_and_last_buckets(self):
        self.assertEqual([b["start"] for b in census.complete_buckets(self.tmp / "buckets.json")], [T0, T0 + 12_600])

    def test_rerun_skips_finished_buckets_without_any_request(self):
        self.run_census()
        before = len(self.fake.requests)
        self.run_census()
        self.assertEqual(len(self.fake.requests), before)

    def test_reconcile_compares_each_bucket_with_x402scan(self):  # AC-4
        db = self.run_census()
        rows = reconcile.by_bucket(db)
        self.assertEqual([(r["w0_transfers"], r["x402scan_transfers"], r["ratio_usdc"]) for r in rows],
                         [(2, 2, 1.0), (0, 0, None)])

    def test_unmarked_facilitator_transaction_is_found_from_its_nonce_and_removed_by_w1(self):  # slice 3 finding
        db = self.run_census()
        self.assertEqual(db.execute("select tx, atomic, reason from removed").fetchall(), [(UH, 7_000, "unmarked")])
        meta = json.loads(db.execute("select meta from buckets where first_block = ?", (MARKED,)).fetchone()[0])
        self.assertEqual(meta["unmarked_facilitator_txs"], 1)

    def test_waterfall_steps_add_up_and_pin_the_inputs(self):  # AC-3, AC-7 for W1
        db = self.run_census()
        w = waterfall.build(db, x402scan_commit="abc", contracts_commit="def")
        self.assertEqual((w["first_block"], w["last_block"]), (T0 // 2, (T0 + 2 * 12_600) // 2 - 1))
        self.assertEqual(w["steps"][0]["remaining_atomic"], 2_507_000)
        self.assertEqual(w["steps"][-1]["remaining_atomic"], w["w1_payments_check"]["atomic"])
        for prev, step in zip(w["steps"], w["steps"][1:]):
            self.assertEqual(step["remaining_atomic"], prev["remaining_atomic"] - step["removed_atomic"] + step["added_atomic"])
        self.assertIn("W1", w["rule_versions"])


if __name__ == "__main__":
    unittest.main()


class NonceGaps(unittest.TestCase):
    def test_bisects_only_where_the_nonce_rose_more_than_the_known_blocks_explain(self):  # S3-S4
        sent = [105, 130, 130, 177]  # blocks of the address's transactions; 130 holds two
        calls = []

        def answer(method, params):
            calls.append(int(params[1], 16))
            return hex(sum(b <= int(params[1], 16) for b in sent))

        fake = FakeRpc(answer)
        self.addCleanup(fake.close)
        rpc = Rpc(fake.url, Path(tempfile.mkdtemp(dir=Path.home() / "scratch")), pause=0)
        self.assertEqual(census.gap_blocks(rpc, FAC, 99, 200, 0, 4, [105, 130, 177]), [130])
        self.assertEqual(census.gap_blocks(rpc, FAC, 99, 200, 0, 4, [105, 130, 130, 177]), [])
        self.assertLess(len(calls), 20)


class Report(unittest.TestCase):
    def test_writes_the_csv_and_waterfall_without_the_hour_check(self):  # S3-P1: AC-2 from an empty out/
        out = Path(tempfile.mkdtemp(dir=Path.home() / "scratch"))
        db = sqlite3.connect(":memory:")
        db.executescript(census.SCHEMA)
        db.execute("insert into buckets values ('b', 1, 2, 2, 200, 1, '{}')")
        db.execute("insert into w0 values ('t1', 0, 'p', 'q', 100, 'f', 's1', 1, 'b')")
        db.execute("insert into transfers values ('t1', 0, 'p', 'q', 100, 'f', 's1', 1, 'b')")
        summary = reconcile.report(db, out, "c", "d")
        self.assertEqual((summary["ratio_usdc"], summary["hour_coverage_check"]), (0.5, "not run"))
        self.assertIn("ratio_transfers", (out / "reconcile/x402scan.csv").read_text().splitlines()[0])
        self.assertEqual(json.loads((out / "waterfall.json").read_text())["reconcile"], summary)


class UnsyncedAddresses(unittest.TestCase):
    def test_traffic_x402scan_no_longer_syncs_is_its_own_added_step(self):
        db = sqlite3.connect(":memory:")
        db.executescript(census.SCHEMA)
        db.execute("insert into buckets values ('b', 1, 2, 0, 0, 1, '{}')")
        db.execute("insert into w0 values ('t1', 0, 'p', 'q', 100, 'f', 's1', 1, 'b')")
        db.execute("insert into w0 values ('t2', 0, 'p', 'q', 40, 'f', 's2', 0, 'b')")
        db.execute("insert into transfers values ('t1', 0, 'p', 'q', 100, 'f', 's1', 1, 'b')")
        db.execute("insert into transfers values ('t2', 0, 'p', 'q', 40, 'f', 's2', 0, 'b')")
        steps = waterfall.build(db, "c", "d")["steps"]
        self.assertEqual((steps[0]["remaining_atomic"], steps[1]["added_atomic"], steps[1]["remaining_atomic"]), (100, 40, 140))
        self.assertEqual(reconcile.by_bucket(db)[0]["w0_usdc"], 100 / 1e6)
