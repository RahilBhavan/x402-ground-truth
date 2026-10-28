"""The site's primary exhibit, built from the run: the largest single payer-payee pair that W4 removes, against what
the rules keep and what the other rules remove, as shares of W1's dollars.

python3 -m ground_truth.figure   # writes out/exhibit/x402-one-pair.exhibit.json, lints and renders it with Proof Desk
The spec and every number on it come from out/waterfall.json and out/settlements.sqlite, so a rerun redraws it.
Rendering needs Proof Desk (~/projects/proof-desk) and uv; the exhibit stays design review pending until Rahil passes it.
"""
import json
import subprocess
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from . import results, rules

ROOT = Path(__file__).resolve().parent.parent
PROOF_DESK = Path.home() / "projects" / "proof-desk"
ID = "x402-one-pair"
WORDS = dict(enumerate("zero one two three four five six seven eight nine ten".split()))


def largest_pair(db):
    """(payments, atomic) of the payer-payee pair with the most dollars among W4's removals. Addresses stay here."""
    pays = results.payments(db)
    steps, _ = rules.apply(pays, results.stored_returns(None, db, pays))
    pairs = defaultdict(lambda: [0, 0])
    for p in next(removed for rule, _, removed in steps if rule == "W4"):
        pairs[(p["payer"], p["payee"])][0] += 1
        pairs[(p["payer"], p["payee"])][1] += p["atomic"]
    return tuple(max(pairs.values(), key=lambda v: v[1])) if pairs else (0, 0)


def spec(w, pair):
    count, atomic = pair
    whole, kept = w["w1_payments_check"]["atomic"] / 1e6, w["kept"]["atomic"] / 1e6
    one, other = atomic / 1e6, whole - atomic / 1e6 - kept
    share = 100 * one / whole
    if share < 50:
        raise SystemExit(f"the largest W4 pair is {share:.1f}% of W1 dollars, not a majority; this exhibit's finding "
                         "does not hold for this run, so write a new one")
    n = WORDS.get(count, f"{count:,}")
    return {
        "id": ID, "series": "Onchain Receipts",
        "title": f"{n.capitalize()} payments carried {share:.0f}% of the week's dollars",
        "key": f"{n.capitalize()} payments",
        "sub": f"Share of ${whole:,.0f} in x402 USDC on Base, Oct 20 to Oct 27, 2026",
        "hero": [f"{share:.0f}%", f"${one:,.0f}, one payer to one payee"],
        "source": f"Base blocks {w['first_block']:,} to {w['last_block']:,}, keyless node.",
        "note": f"Without the {count}, the rules keep {100 * kept / (whole - one):.0f}%, not {100 * kept / whole:.0f}%.",
        "stamp": f"CHECKED · {count} RECEIPTS ON A BASE NODE",
        "form": "hbars", "illustration": False,
        "params": {"rows": [["One pair", round(share, 2), f"${one:,.0f}"],
                            ["Kept", round(100 * kept / whole, 2), f"${kept:,.0f}"],
                            ["Other rules", round(100 * other / whole, 2), f"${other:,.0f}"]],
                   "xmax": 100, "digits": 0},
        "derived": [{"value": f"{share:.0f}%", "expr": f"100 * {one} / {whole}", "digits": 0},
                    {"value": f"{100 * kept / (whole - one):.0f}%", "expr": f"100 * {kept} / ({whole} - {one})", "digits": 0},
                    {"value": f"{100 * kept / whole:.0f}%", "expr": f"100 * {kept} / {whole}", "digits": 0},
                    {"value": f"${other:,.0f}", "expr": f"{whole} - {one} - {kept}", "digits": 0},
                    {"value": f"${whole:,.0f}", "expr": f"{whole}", "digits": 0}],
    }


def build(out=ROOT / "out"):
    w = json.loads((out / "waterfall.json").read_text())
    pair = largest_pair(sqlite3.connect(out / "settlements.sqlite"))
    folder = out / "exhibit"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{ID}.exhibit.json"
    path.write_text(json.dumps(spec(w, pair), indent=1, ensure_ascii=False))
    (folder / "figure.json").write_text(json.dumps({"pair_count": pair[0], "pair_atomic": pair[1]}))
    pd = [sys.executable, "-m", "proofdesk.cli", "research"]
    subprocess.run(pd + ["lint", str(path)], cwd=PROOF_DESK, check=True)
    subprocess.run(pd + ["render", "--spec", str(path), "--out", str(folder), "--sizes", "landscape"], cwd=PROOF_DESK,
                   check=True)
    return path


if __name__ == "__main__":
    print(build())
