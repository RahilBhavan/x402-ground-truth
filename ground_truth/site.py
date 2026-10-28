"""Slice 5: three static pages built from a complete run (docs/prd/3-build.md section 11), readable with JavaScript off.

site/index.html (the answer), site/rules.html (schemes and rules W0-W5), site/method.html (falsifiers, data, rerun).
Pages use the rahil-design renderer's document() for tokens, embedded fonts and components.css. Payer and payee
addresses never reach a page: examples are transaction hashes only (PRD open question 1, AC-15).
"""
import csv
import hashlib
import html
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from .rules import BASE_GENESIS_TS

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = Path("/home/rahil/.t3/projects/main/.agents/skills/rahil-design")
REPO = "https://github.com/RahilBhavan/x402-ground-truth/blob/main"
BASESCAN = "https://basescan.org/tx/"
FIGURE = "one-pair-light-landscape.png"  # from out/exhibit/, written by python3 -m ground_truth.figure

# AC-11: published figures beside this project's window, from research/sources.md.
PUBLISHED = (
    ("Visa and Artemis, adjusted", "May 2025 to 2026-04-21", "All x402 chains",
     "$15.0M adjusted of $135.7M raw (11.05% of dollars kept); wash and test filters are proprietary",
     "2026-07", "no: since launch, all chains", "D1, D3"),
    ("Artemis, 30-day adjusted", "30 days, month unconfirmed", "Unstated",
     "$1.6M after a filter for wallets paying themselves or cycling funds (search snippet only)",
     "about 2026-03", "no: different month, snippet only", "D5"),
    ("Jan Curn (Apify), talk", "30 days to mid-October 2026", "Probably all chains",
     "About $1M of x402 volume read from x402scan", "2026-10-19", "no: all chains, approximate", "E1, E5"),
    ("BeInCrypto report", "2026-07-23 to 2026-08-26", "About 94.5% Solana",
     "6.4M payments and $119,947", "2026-10-07", "no: about 94.5% Solana", "E3, E4, E5"),
)

RULES = (  # (rule, one sentence with {thresholds}, function)
    ("W0", "x402scan's own filter: every USDC transfer in a transaction sent by a synced listed facilitator address, "
           "with pass-through chains merged into one row.", "ground_truth/x402scan_filter.py"),
    ("W1", "Keeps one row per x402 payment: removes transfers with no x402 marker, non-payments, second hops and "
           "batch channel movements, and adds batch claims.", "ground_truth/settlements.py"),
    ("W2", "Removes a payment whose payer and payee are the same address.", "ground_truth/rules.py"),
    ("W3", "Removes a payment when the payee sends at least {w3_pct}% of it back to the payer within 24 hours.",
     "ground_truth/rules.py"),
    ("W4", "Removes payments to a payee with fewer than {w4_payments} payments or fewer than {w4_payers} distinct payers in the window.",
     "ground_truth/rules.py"),
    ("W5", "Removes payments from a payer-payee pair that made at least {w5_burst:,} payments of one identical amount in "
           "one UTC day.", "ground_truth/rules.py"),
)
W2_NOTE = ("W2 catches only a wallet paying itself. Self-dealing across several wallets is not detected in v1; "
           "W3 and W5 catch some of it.")
SCHEMES = (("eip3009", "Exact, EIP-3009"), ("exact_proxy", "Exact, Permit2 proxy"), ("upto", "Upto"),
           ("batch_settlement", "Batch settlement claims"))

CSS = """
.site table{border-collapse:collapse;display:block;overflow-x:auto;max-width:100%;margin:20px 0;font-size:var(--size-15)}
.site th,.site td{border-top:1px solid var(--color-border);padding:10px 12px;text-align:left;vertical-align:top}
.site th{color:var(--color-secondary);font-weight:600}
.site td.n,.site th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.site tr.kept td{font-weight:600}
.site code{font-family:var(--font-code);font-size:var(--size-15);overflow-wrap:anywhere}
.site h2{margin-top:56px}
.site .figure img{display:block;width:100%;height:auto}
.site .keys{display:grid;grid-template-columns:repeat(auto-fit,minmax(10rem,1fr));gap:16px;margin:24px 0;padding:0}
.site .keys div{border-top:3px solid var(--color-accent);padding-top:8px}
.site .keys dt{color:var(--color-secondary);font-size:var(--size-15)}
.site .keys dd{margin:0;font-family:var(--font-code);font-size:var(--size-22);font-variant-numeric:tabular-nums}
.site .answer{padding:40px 0 24px}
.site .answer h1{font-size:var(--size-fluid-30-44);line-height:1.15;max-width:30ch;margin:0 0 16px}
.site .answer p{max-width:62ch}
.site .run{color:var(--color-secondary);font-size:var(--size-15)}
.site .hashes a{font-family:var(--font-code);font-size:var(--size-15);overflow-wrap:anywhere}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def usd(atomic):
    return f"${atomic / 1e6:,.2f}"


def block_time(block):
    return datetime.fromtimestamp(BASE_GENESIS_TS + 2 * block, timezone.utc)


def window(w):
    """Window bounds from the pinned blocks: the first block's time and the end of the last block's 2 seconds."""
    a, b = block_time(w["first_block"]), block_time(w["last_block"] + 1)
    return a.strftime("%b %-d, %Y %H:%M"), b.strftime("%b %-d, %Y %H:%M")


def headline(w):
    start, end = window(w)
    return (f"Of {usd(w['steps'][0]['remaining_atomic'])} in x402 payments counted on Base from {start} to {end} UTC, "
            f"{usd(w['kept']['atomic'])} passes five published rules.")


def table(head, rows, numeric=(), classes=()):
    th = "".join(f'<th{" class=n" if i in numeric else ""} scope="col">{esc(h)}</th>' for i, h in enumerate(head))
    body = "".join(
        f'<tr{f" class={classes[r]}" if r < len(classes) and classes[r] else ""}>'
        + "".join(f'<td{" class=n" if i in numeric else ""}>{c}</td>' for i, c in enumerate(row)) + "</tr>"
        for r, row in enumerate(rows))
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def page(title, active, run_line, main):
    nav = "".join(f'<a href="{href}"{" aria-current=page" if href == active else ""}>{name}</a>'
                  for href, name in (("index.html", "Answer"), ("rules.html", "Rules"), ("method.html", "Method and data")))
    version = (BUNDLE / "VERSION").read_text().strip()
    body = (f'<a class="skip" href="#main">Skip to content</a><div class="page site">'
            f'<header class="site-header"><a class="brand" href="index.html">x402 ground truth</a>'
            f'<nav class="nav" aria-label="Pages">{nav}</nav></header>'
            f'<main id="main"><p class="run">{run_line}</p>{main}</main>'
            f'<footer class="footer">Rahil Bhavan · rahil-design {esc(version)} · Design review pending · '
            f'Public onchain data only</footer></div>')
    sys.path.insert(0, str(BUNDLE / "scripts"))
    from render_markup import document
    return document(f"{title} · x402 ground truth", body, extra_css=CSS)


def run_line(w, run_date):
    return (f"This page shows the run of {run_date} for blocks {w['first_block']:,}–{w['last_block']:,}. "
            "It is not live.")


def steps_table(w):
    rows, classes = [], []
    for s in w["steps"]:
        change = (f"−{usd(s['removed_atomic'])}" if s["removed_count"] else
                  f"+{usd(s['added_atomic'])}" if s["added_count"] else "")
        count = (f"−{s['removed_count']:,}" if s["removed_count"] else f"+{s['added_count']:,}" if s["added_count"] else "")
        rows.append([esc(s["rule"]), esc(s["label"]), count, change, f"{s['remaining_count']:,}",
                     usd(s["remaining_atomic"])])
        classes.append("")
    rows.append(["", "<strong>Kept</strong>", "", "", f"{w['kept']['count']:,}", usd(w["kept"]["atomic"])])
    classes.append("kept")
    return table(["Rule", "Step", "Payments", "USDC", "Payments left", "USDC left"], rows, numeric=(2, 3, 4, 5),
                 classes=classes)


def index(w, run_date, figure_meta, captured):
    w0, kept = w["steps"][0], w["kept"]
    rec = w["reconcile"]
    start, end = window(w)
    figure = (f'<figure class="figure"><img src="{FIGURE}" width="1200" height="675" alt="{esc(alt(w, figure_meta))}">'
              f'<figcaption class="sources">Every step, in order, is in the table below.</figcaption></figure>'
              if figure_meta else "")
    keys = (("Counted by x402scan's method", usd(w0["remaining_atomic"])), ("Kept by all five rules", usd(kept["atomic"])),
            ("Payments kept", f"{kept['count']:,}"),
            ("Share of dollars kept", f"{100 * kept['atomic'] / w0['remaining_atomic']:.1f}%"))
    keyrow = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in keys)
    published = [["This project, W0 (x402scan's filter)", f"{start} to {end} UTC", "Base",
                  f"{usd(w0['remaining_atomic'])} across {w0['remaining_count']:,} rows", run_date, "yes: same blocks",
                  "this run"],
                 ["x402scan, its 47 buckets", f"{start} to {end} UTC", "Base",
                  f"${rec['x402scan_usdc']:,.2f} across {rec['x402scan_transfers']:,} rows (W0 ratio "
                  f"{rec['ratio_usdc']:.4f})", captured, "yes: same buckets", "O2"]]
    published += [[esc(c) for c in row] for row in PUBLISHED]
    main = (f'<section class="answer"><div><h1>{esc(headline(w))}</h1></div></section>{figure}'
            f'<dl class="keys">{keyrow}</dl>'
            f'<section class="story"><h2>Every step</h2>{steps_table(w)}</section>'
            f'<section class="story"><h2>Published figures beside this window</h2>'
            f'<p>Only figures with the same blocks are comparable. The others differ in window, chain or method, so the '
            f'gap between them is not a measure of fake traffic.</p>'
            + table(["Figure", "Window", "Chains", "Definition and value", "Published", "Comparable", "Source"],
                    published) +
            f'</section><section class="story"><h2>Pinned run</h2>'
            f'<p>Base blocks {w["first_block"]:,} to {w["last_block"]:,}; facilitator list at x402scan commit '
            f'<code>{esc(w["x402scan_commit"][:12])}</code>; rule versions '
            f'{esc(", ".join(f"{k} {v}" for k, v in sorted(w["rule_versions"].items())))}. '
            f'Rerun and file hashes are on <a href="method.html">Method and data</a>.</p></section>')
    return page("Answer", "index.html", run_line(w, run_date), main)


def alt(w, meta):
    """The exhibit's labelled values, from the same run (ground_truth/figure.py)."""
    w1, kept, pair = w["w1_payments_check"]["atomic"], w["kept"]["atomic"], meta["pair_atomic"]
    return (f"Bar chart of {usd(w1)} in x402 USDC on Base after W1, as shares. One payer-payee pair, "
            f"{meta['pair_count']:,} payments that W4 removes: {usd(pair)}, {100 * pair / w1:.0f}%. Kept by all rules: "
            f"{usd(kept)}, {100 * kept / w1:.0f}%. Removed by the other rules: {usd(w1 - pair - kept)}.")


def rules_page(w, run_date, schemes, examples, sensitivity):
    t = {**w["thresholds"], "w3_pct": round(100 * w["thresholds"]["w3_share"])}
    by_rule = {}
    for s in w["steps"][1:]:
        by_rule.setdefault(s["rule"], []).append(s)
    sections = []
    for rule, sentence, path in RULES:
        steps = by_rule.get(rule, [])
        rows = [[esc(s["label"]), f"{s['removed_count']:,}" if s["removed_count"] else f"+{s['added_count']:,}",
                 f"−{usd(s['removed_atomic'])}" if s["removed_count"] else f"+{usd(s['added_atomic'])}",
                 f"{s['dust_removed_count']:,}"] for s in steps]
        moved = table(["Step", "Payments", "USDC", "Of which dust (under 1 cent)"], rows, numeric=(1, 2, 3)) if rows else ""
        sens = "".join(
            f'<p>Sensitivity, {esc(r["threshold"])} (default {esc(r["default"])}): kept '
            f'${float(r["kept_usdc_0.5x"]):,.2f} at 0.5x, ${float(r["kept_usdc_1x"]):,.2f} at 1x, '
            f'${float(r["kept_usdc_2x"]):,.2f} at 2x.</p>'
            for r in sensitivity if r["threshold"].startswith(rule.lower() + "_"))
        ex = examples.get(rule, [])
        hashes = "".join(f'<li><a href="{BASESCAN}{esc(e["tx"])}">{esc(e["tx"])}</a> · block {int(e["block"]):,} · '
                         f'{usd(int(e["atomic"]))}</li>' for e in ex)
        note = f"<p>{esc(W2_NOTE)}</p>" if rule == "W2" else ""
        sections.append(f'<section class="story" id="{rule.lower()}"><h2>{rule}</h2><p>{esc(sentence.format(**t))} '
                        f'<a href="{REPO}/{path}">Code</a>.</p>{note}{moved}{sens}'
                        + (f'<h3>Examples</h3><ol class="hashes">{hashes}</ol>' if hashes else "") + "</section>")
    scheme_rows = [[esc(name), f"{schemes.get(k, (0, 0))[0]:,}", usd(schemes.get(k, (0, 0))[1])] for k, name in SCHEMES]
    main = (f'<section class="answer"><div><h1>Rules W0 to W5</h1><p>A payment leaves at the first rule it fails. '
            f'Thresholds were fixed in the <a href="{REPO}/docs/preregistration.md">pre-registration</a> before the '
            f'7-day census ran. Examples are transaction hashes only.</p></div></section>'
            f'<section class="story"><h2>Payments by scheme, after W1</h2>'
            + table(["Scheme", "Payments", "USDC"], scheme_rows, numeric=(1, 2)) + "</section>" + "".join(sections))
    return page("Rules", "rules.html", run_line(w, run_date), main)


def falsifiers(root):
    text = (root / "docs" / "preregistration.md").read_text()
    part = text.split("## Falsifiers", 1)[1].split("\n## ", 1)[0]
    items = [line.split(". ", 1)[1] for line in part.splitlines() if line[:2].rstrip(".").isdigit()]
    strip = lambda s: s.replace("**", "")
    return "".join(f"<li>{esc(strip(i))}</li>" for i in items)


def method_page(w, run_date, out, root, captured):
    files = [p for p in (out / "waterfall.json", out / "sensitivity.csv", out / "reconcile" / "x402scan.csv") if p.exists()]
    hashes = [[f"<code>out/{esc(p.relative_to(out))}</code>", f"<code>{hashlib.sha256(p.read_bytes()).hexdigest()}</code>"]
              for p in files]
    buckets = sorted((out / "reconcile").glob("x402scan-buckets-*.json"))
    rerun = f"python3 -m ground_truth run --buckets out/reconcile/{buckets[-1].name if buckets else '<capture>.json'}"
    main = (f'<section class="answer"><div><h1>Method and data</h1></div></section>'
            f'<section class="story"><h2>Pre-registered falsifiers</h2><ol>{falsifiers(root)}</ol></section>'
            f'<section class="story"><h2>Data</h2><ul>'
            f'<li>Base mainnet through the keyless nodes base-rpc.publicnode.com and blastapi: USDC '
            f'<code>AuthorizationUsed</code> and <code>Transfer</code> logs, the three x402 proxies\' logs, senders and '
            f'receipts.</li>'
            f'<li>Facilitator addresses from Merit-Systems/x402scan at commit <code>{esc(w["x402scan_commit"])}</code>.</li>'
            f'<li>x402scan\'s 47 bucketed 7-day Base totals from its free page route, captured {captured}.</li>'
            f'<li>Published figures as listed in <a href="{REPO}/research/sources.md">research/sources.md</a>.</li></ul>'
            f'</section><section class="story"><h2>Rerun</h2><pre class="code"><code>{esc(rerun)}</code></pre>'
            f'<p>The run reads only public data and needs no key. The rerun checks are recorded in <a href="{REPO}/docs/slices/">docs/slices/</a>.</p>'
            + table(["File", "SHA-256"], hashes) +
            f'</section><section class="story"><h2>Known limits</h2><ul>'
            f'<li>One frozen window of {(w["last_block"] + 1 - w["first_block"]) / 1800:g} hours on Base only; not live.</li>'
            f'<li>W2 sees one wallet paying itself, not rings of wallets.</li>'
            f'<li>Batch channels opened more than 2M blocks before the window stay unknown: the keyless node refuses '
            f'older state.</li>'
            f'<li>Rules describe patterns. A removed payment is not a claim that anyone committed fraud.</li></ul></section>')
    return page("Method and data", "method.html", run_line(w, run_date), main)


def read_csv(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def build(out, site, root=ROOT):
    site.mkdir(parents=True, exist_ok=True)
    wf = out / "waterfall.json"
    w = json.loads(wf.read_text()) if wf.exists() else None
    if not w or "kept" not in w:
        empty = ('<section class="answer"><div><h1>No pinned run yet. Run <code>python -m ground_truth run</code> '
                 'to build one.</h1></div></section>')
        for stale in ("rules.html", "method.html", FIGURE):
            (site / stale).unlink(missing_ok=True)
        (site / "index.html").write_text(page("Answer", "index.html", "", empty))
        return None
    run_date = datetime.fromtimestamp(wf.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
    rendered = sorted((out / "exhibit").glob("*x402-one-pair-landscape-light.png"))
    meta = json.loads((out / "exhibit" / "figure.json").read_text()) if rendered else None
    (site / FIGURE).unlink(missing_ok=True)
    if rendered:
        shutil.copyfile(rendered[-1], site / FIGURE)
    buckets = sorted((out / "reconcile").glob("x402scan-buckets-*.json"))
    captured = buckets[-1].stem.removeprefix("x402scan-buckets-")[:10] if buckets else "unknown"
    db = sqlite3.connect(out / "settlements.sqlite")
    schemes = {k: (n, a) for k, n, a in db.execute("select scheme, count(*), sum(atomic) from payments group by scheme")}
    examples = {p.stem: read_csv(p) for p in sorted((out / "examples").glob("*.csv"))}
    sensitivity = read_csv(out / "sensitivity.csv")
    (site / "index.html").write_text(index(w, run_date, meta, captured))
    (site / "rules.html").write_text(rules_page(w, run_date, schemes, examples, sensitivity))
    (site / "method.html").write_text(method_page(w, run_date, out, root, captured))
    return w


if __name__ == "__main__":
    build(ROOT / "out", ROOT / "site")
    print(f"wrote {ROOT / 'site'}", file=sys.stderr)
