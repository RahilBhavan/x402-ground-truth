import csv
import json
import tempfile
import unittest
from pathlib import Path

from ground_truth import results, rules, site, waterfall
from scripts import check_site
from tests.fixtures import OTHER, PAYEE, PAYER, ROUTER
from tests.test_waterfall import db_with

HAVE_BUNDLE = (site.BUNDLE / "scripts" / "render_markup.py").exists()
PAYERS = [PAYER, OTHER, ROUTER, "0x" + "5" * 40]


def fixture_out(folder):
    """A complete run in miniature: settlements.sqlite, waterfall.json, sensitivity.csv and examples."""
    db_path = folder / "settlements.sqlite"
    mem = db_with([(PAYEE, PAYEE, 5_000)] + [(p, PAYEE, 20_000) for p in PAYERS])
    disk = __import__("sqlite3").connect(db_path)
    mem.commit()
    mem.backup(disk)
    pays = results.payments(disk)
    steps, kept = rules.apply(pays, [])
    w = waterfall.build(disk, "5732bb83" + "0" * 32, "d", later_rules=steps)
    w.update(kept={"count": len(kept), "atomic": sum(p["atomic"] for p in kept)}, thresholds=rules.DEFAULTS,
             reconcile={"x402scan_usdc": 0.1, "x402scan_transfers": 5, "ratio_usdc": 1.0})
    (folder / "waterfall.json").write_text(json.dumps(w))
    with (folder / "sensitivity.csv").open("w", newline="") as f:
        c = csv.DictWriter(f, fieldnames=list(results.sensitivity(pays, [])[0]))
        c.writeheader()
        c.writerows(results.sensitivity(pays, []))
    (folder / "exhibit").mkdir()
    (folder / "exhibit" / "022-x402-one-pair-landscape-light.png").write_bytes(b"png")
    (folder / "exhibit" / "figure.json").write_text(json.dumps({"pair_count": 1, "pair_atomic": 5_000}))
    (folder / "examples").mkdir()
    (folder / "examples" / "W2.csv").write_text(f"tx,block,atomic\n0x{0:064x},150,5000\n")
    return w


@unittest.skipUnless(HAVE_BUNDLE, "needs the rahil-design bundle on this machine")
class Site(unittest.TestCase):
    def test_pages_carry_the_waterfall_totals_and_no_wallet_address(self):  # AC-12, AC-15
        with tempfile.TemporaryDirectory() as tmp:
            out, folder = Path(tmp) / "out", Path(tmp) / "site"
            out.mkdir()
            w = fixture_out(out)
            site.build(out, folder)
            self.assertEqual(sorted(p.name for p in folder.iterdir()),
                             ["index.html", "method.html", site.FIGURE, "rules.html"])
            self.assertEqual(check_site.main(out, folder), 0)
            index = (folder / "index.html").read_text()
            self.assertIn(site.usd(w["kept"]["atomic"]), index)
            self.assertIn("no: about 94.5% Solana", index)  # AC-11
            self.assertIn(f"basescan.org/tx/0x{0:064x}", (folder / "rules.html").read_text())

    def test_an_address_on_a_page_fails_the_check(self):  # AC-15
        with tempfile.TemporaryDirectory() as tmp:
            out, folder = Path(tmp) / "out", Path(tmp) / "site"
            out.mkdir()
            fixture_out(out)
            site.build(out, folder)
            (folder / "rules.html").write_text((folder / "rules.html").read_text() + PAYEE.upper().replace("0X", "0x"))
            self.assertEqual(check_site.main(out, folder), 1)

    def test_no_run_yet_writes_only_the_empty_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "site"
            folder.mkdir()
            (folder / "rules.html").write_text("stale")
            site.build(Path(tmp) / "missing", folder)
            self.assertIn("No pinned run yet", (folder / "index.html").read_text())
            self.assertEqual([p.name for p in folder.iterdir()], ["index.html"])


if __name__ == "__main__":
    unittest.main()
