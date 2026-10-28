"""AC-12, AC-15 and the figure part of AC-13: the headline on site/index.html carries out/waterfall.json's W0 and kept totals and the window
dates, and no payer or payee address from out/settlements.sqlite appears in any file under site/."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ground_truth import site  # noqa: E402


def headline_ok(w, index_html):
    start, end = site.window(w)
    want = [site.usd(w["steps"][0]["remaining_atomic"]), site.usd(w["kept"]["atomic"]), start, end]
    h1 = index_html.split("<h1>", 1)[1].split("</h1>", 1)[0]
    return [v for v in want if v not in h1]


def leaked(db, folder):
    addresses = set()
    for table in ("transfers", "w0", "payments"):
        for payer, payee in db.execute(f"select payer, payee from {table}"):
            addresses |= {a.lower() for a in (payer, payee) if a and a.startswith("0x")}
    found = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        text = path.read_bytes().decode("utf-8", "replace").lower()
        found += [(path.name, a) for a in addresses if a in text]
    return len(addresses), found


def main(out=Path("out"), folder=Path("site")):
    w = json.loads((out / "waterfall.json").read_text())
    missing = headline_ok(w, (folder / "index.html").read_text())
    print("AC-12 headline:", "ok" if not missing else f"missing {missing}")
    figure = (folder / site.FIGURE).exists() and f'src="{site.FIGURE}"' in (folder / "index.html").read_text()
    print("AC-13 figure:", "ok" if figure else "missing; run python3 -m ground_truth.figure, then rebuild")
    n, found = leaked(sqlite3.connect(out / "settlements.sqlite"), folder)
    print(f"AC-15 addresses: {n:,} payer and payee addresses checked, {len(found)} found in site/")
    for name, a in found[:10]:
        print(f"  {name}: {a}")
    return 1 if missing or found or not figure else 0


if __name__ == "__main__":
    sys.exit(main())
