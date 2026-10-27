"""Build build/plan.html: the PRD, its diagrams, the review record and slice 1 on one page.

uv run --with markdown python scripts/plan_page.py
Diagrams come from build/diagrams/diagram-N.svg (written by prd-loop's check_prd.py --render-dir).
"""
import html
import json
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "plan.html"

CSS = """
:root{--ink:#15202b;--muted:#526272;--line:#c5d0db;--paper:#fff;--panel:#f5f7fa;--accent:#1652f0;
--warning:#85230e;--warning-bg:#fff0e8;--safe:#115c38;--safe-bg:#e8f6ee}
*{box-sizing:border-box}body{background:#e8edf2;color:var(--ink);margin:0;
font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
header,main{background:var(--paper);margin:0 auto;max-width:76rem;padding:1.5rem 2rem}
.label{background:var(--warning);color:#fff;font-weight:800;letter-spacing:.06em;margin:-1.5rem -2rem 1.5rem;
padding:.6rem 2rem;text-align:center}
h1,h2,h3{line-height:1.2;text-wrap:balance}h2{border-bottom:2px solid var(--ink);padding-bottom:.35rem;margin-top:2.5rem}
p,li{text-wrap:pretty}.muted{color:var(--muted)}
.summary{background:#eef3ff;border-left:4px solid var(--accent);border-radius:.5rem;padding:1rem 1.25rem;margin:1rem 0}
.summary .answer{font-size:1.15rem;font-weight:750;margin:.2rem 0 .6rem}
.keys{display:grid;gap:.75rem;grid-template-columns:repeat(auto-fit,minmax(11rem,1fr));margin:1rem 0}
.key{background:var(--panel);border:1px solid var(--line);border-radius:.5rem;padding:.75rem 1rem}
.key b{display:block;font-size:1.5rem;font-variant-numeric:tabular-nums}.key span{color:var(--muted);font-size:.9rem}
.ask{background:var(--warning-bg);border-left:4px solid var(--warning);border-radius:.5rem;padding:1rem 1.25rem}
.ok{background:var(--safe-bg);border-left:4px solid var(--safe);border-radius:.5rem;padding:1rem 1.25rem}
table{border-collapse:collapse;display:block;overflow-x:auto;width:100%;font-size:.92rem;margin:1rem 0}
th,td{border-bottom:1px solid var(--line);padding:.45rem .6rem;text-align:left;vertical-align:top}
th{background:var(--panel)}td{font-variant-numeric:tabular-nums}
code{background:var(--panel);border-radius:.25rem;padding:.05rem .3rem;font-size:.88em;overflow-wrap:anywhere}
figure{border:1px solid var(--line);border-radius:.5rem;margin:1rem 0;padding:1rem;overflow-x:auto}
figure svg{display:block;height:auto;margin:0 auto;max-width:100%}
nav{display:flex;flex-wrap:wrap;gap:.4rem 1rem;font-size:.92rem;margin-top:.75rem}nav a{color:var(--accent)}
.sev-high{color:var(--warning);font-weight:700}
@media (max-width:40rem){header,main{padding:1rem}.label{margin:-1rem -1rem 1rem}}
"""


def md(text):
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


def prd_html():
    text = (ROOT / "docs/prd.md").read_text()
    svgs = sorted((ROOT / "build/diagrams").glob("diagram-*.svg"))
    blocks = iter(svgs)

    def to_svg(_):
        svg = next(blocks, None)
        if svg is None:
            return "<p><em>Diagram not rendered. Run check_prd.py with --render-dir build/diagrams.</em></p>"
        body = re.sub(r"^<\?xml[^>]*>", "", svg.read_text())
        return f"\n\n<figure>{body}</figure>\n\n"

    text = re.sub(r"```mermaid\n.*?```", to_svg, text, flags=re.S)
    text = text.split("\n---\n", 1)[1]  # header lines are shown in the page header instead
    return md(text)


def review_html():
    r1 = json.loads((ROOT / "review/round-1.json").read_text())
    fix = {x["id"]: x for x in json.loads((ROOT / "review/round-1-repair.json").read_text())["responses"]}
    ver = {x["id"]: x for x in json.loads((ROOT / "review/round-1-verify.json").read_text())["results"]}
    rows = "".join(
        f"<tr><td>{f['id']}</td><td class='sev-{f['severity']}'>{f['severity']}</td>"
        f"<td>{html.escape(f['claim'])}</td><td>{fix[f['id']]['status']}: {html.escape(fix[f['id']]['where'])}</td>"
        f"<td>{ver[f['id']]['verdict']}</td></tr>" for f in r1["findings"])
    return ("<table><thead><tr><th>#</th><th>Severity</th><th>Finding</th><th>Repair</th><th>Verified</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>")


def main():
    hour = json.loads((ROOT / "out/s1/hour.json").read_text())
    cap = json.loads((ROOT / "out/reconcile/x402scan-capture.json").read_text())
    s1 = (ROOT / "docs/slices/s1.md").read_text().split("\n", 1)[1]
    keys = [
        (f"{hour['w1']['payments']:,}", "x402 payments in the hour"),
        (f"${hour['w1']['usdc']:,.2f}", "USDC they moved (W1)"),
        (f"${hour['w0_visible']['usdc']:,.2f}", "x402scan's method on the same txs (W0)"),
        (f"{hour['dust_under_1_cent']['share_of_payments']:.1%}", "of payments under 1 cent"),
        (f"${cap['usdc']:,.0f}", f"x402scan 7-day Base figure, captured {cap['captured_at'][:10]}"),
    ]
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>x402 ground truth: plan and slice 1</title>
<style>{CSS}</style></head><body>
<header><div class="label">DRAFT PLAN · NOT PUBLISHED · NO RESULTS YET BEYOND ONE HOUR</div>
<h1>x402 ground truth</h1>
<p class="muted">How much of x402's reported Base volume survives named, rerunnable exclusion rules. Owner Rahil Bhavan ·
PRD status DRAFT · 2026-10-27 · local repo, no remote</p>
<div class="summary"><p class="answer">Slice 1: in the hour from {hour['hour_start_utc'].replace('T', ' ').rstrip('Z')} UTC
(blocks {hour['first_block']:,}–{hour['last_block']:,}), {hour['w1']['payments']:,} x402 payments moved
${hour['w1']['usdc']:,.2f} through x402scan's listed facilitators.</p>
<p>One hour is not a rate. The 7-day waterfall is slice 3.</p></div>
<div class="keys">{''.join(f'<div class="key"><b>{v}</b><span>{k}</span></div>' for v, k in keys)}</div>
<div class="ask"><strong>Waiting on Rahil.</strong> Is any line of the PRD wrong? Open calls: addresses on public pages
(hashes only until answered), an optional census key, and creating the public repo, site and any post.</div>
<nav><a href="#prd">PRD</a><a href="#review">Red-team review</a><a href="#slice1">Slice 1</a></nav></header>
<main>
<section id="prd">{prd_html()}</section>
<section id="review"><h2>Red-team review, round 1</h2>
<div class="ok">10 findings from a fresh reviewer; all 10 repaired once and confirmed by a separate verifier.</div>
{review_html()}</section>
<section id="slice1"><h2>Slice 1: one hour, one number</h2>{md(s1)}</section>
</main></body></html>"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(page)
    print(OUT)


if __name__ == "__main__":
    main()
