"""Build build/plan.html in the rahil-design system: plan, diagrams, review record and slice 1.

uv run --with markdown python scripts/plan_page.py
Uses the rahil-design renderer's document() for tokens, embedded fonts and components.css.
The PRD keeps Mermaid source for GitHub; this page redraws the three diagrams as token-styled HTML.
"""
import html
import json
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = Path("/home/rahil/.t3/projects/main/.agents/skills/rahil-design")
sys.path.insert(0, str(BUNDLE / "scripts"))
from render_markup import document  # noqa: E402

OUT = ROOT / "build" / "plan.html"

CSS = """
.plan table{border-collapse:collapse;display:block;overflow-x:auto;width:100%;margin:20px 0;font-size:var(--size-15)}
.plan th,.plan td{border-top:1px solid var(--color-border);padding:10px 12px;text-align:left;vertical-align:top}
.plan th{color:var(--color-secondary);font-weight:600}
.plan td{font-variant-numeric:tabular-nums}
.plan code{font-family:var(--font-code);font-size:var(--size-15);overflow-wrap:anywhere}
.plan h2{margin-top:64px}
.plan .figure svg{display:block;height:auto;margin:0 auto;max-width:100%}
.bridge h3{font-family:var(--font-body);font-weight:600;text-transform:none;font-size:var(--size-22);line-height:1.25;
margin:0 0 20px;color:var(--color-figure-ink);max-width:34ch}
.bridge .row{display:grid;grid-template-columns:minmax(0,13rem) minmax(0,1fr) 6rem;gap:12px;align-items:center;
padding:10px 0;color:var(--color-figure-ink);font-size:var(--size-16)}
.bridge .track{position:relative;height:24px}
.bridge .bar{position:absolute;top:0;bottom:0;border-radius:var(--radius-mark)}
.bridge .w0{background:var(--chart-series-1)}
.bridge .hop{background:var(--chart-series-3)}
.bridge .kept{background:var(--chart-highlight);outline:2px solid var(--chart-series-1);outline-offset:-2px}
.bridge .value{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.bridge .sources{color:var(--color-figure-secondary);font-size:var(--size-15);max-width:none}
.site-hero h1{margin-bottom:24px}
.diagram-html{color:var(--color-figure-ink)}
.flow{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.flow li{border:2px solid var(--chart-series-1);border-radius:var(--radius-control);padding:12px 14px;display:grid;gap:4px;
font-size:var(--size-15);counter-increment:step}
.flow li strong{font-size:var(--size-17)}
.flow li strong::before{content:counter(step) ". "}
.ladder{list-style:none;margin:0;padding:0}
.ladder li{display:grid;grid-template-columns:3.5rem minmax(0,1fr) minmax(0,15rem);gap:12px;align-items:baseline;
padding:12px 0;border-top:1px solid var(--color-figure-border);font-size:var(--size-16)}
.ladder li b{font-size:var(--size-18)}
.ladder li em{font-style:normal;color:var(--color-figure-secondary)}
.ladder li.kept{background:var(--chart-highlight);outline:2px solid var(--chart-series-1);outline-offset:-2px;
border-radius:var(--radius-mark);padding:12px}
.gate{margin:16px 0 0;font-size:var(--size-15);color:var(--color-figure-secondary)}
.slices .row{grid-template-columns:minmax(0,15rem) minmax(0,1fr) 3rem 8rem}
.slices .due{color:var(--color-figure-secondary);font-size:var(--size-15)}
@media(max-width:700px){.flow{grid-template-columns:1fr}.ladder li{grid-template-columns:3rem minmax(0,1fr)}
.ladder li em{grid-column:2}.slices .row{grid-template-columns:1fr 3rem}.slices .due{grid-column:1/-1}}
.waiting{border-left:3px solid var(--color-accent);padding-left:16px;max-width:62ch}
@media(max-width:600px){.bridge .row{grid-template-columns:1fr 5rem}.bridge .track{grid-column:1/-1;grid-row:2}}
"""


def md(text):
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


STEPS = [
    ("Pinned inputs", "7 days of Base blocks ending at the x402scan capture; facilitator list at x402scan commit 5732bb83"),
    ("Logs", "USDC AuthorizationUsed, plus Settled events from the three x402 proxies"),
    ("Senders and receipts", "each transaction's sender; receipts only for facilitator-sent ones"),
    ("settlements.sqlite", "one row per authorization: payer, payee, amount, scheme, facilitator"),
    ("Rules W0–W5", "versioned functions, each with its own count and examples"),
    ("Outputs", "waterfall.json, sensitivity.csv, examples, README and site"),
]
RULES = [
    ("W0", "Is the transaction sent by a listed facilitator?", "No: not x402, outside W0"),
    ("W1", "Does it carry AuthorizationUsed or a proxy Settled event, and is this the payer's own hop?", "No: non-payment transfer or second hop"),
    ("W2", "Is the payer different from the payee?", "No: self-payment"),
    ("W3", "Does the payee send less than 90% back to the payer within 24 hours?", "No: round trip"),
    ("W4", "Does the payee have at least 3 surviving payments from at least 2 payers?", "No: thin seller"),
    ("W5", "Did the pair make fewer than 1,000 identical payments that UTC day?", "No: farming burst"),
]


def flow():
    steps = "".join(f'<li><strong>{t}</strong><span>{d}</span></li>' for t, d in STEPS)
    return (f'<figure class="figure diagram-html"><ol class="flow">{steps}</ol>'
            '<p class="gate">Gate: one hour is also scanned block by block. If the scan finds facilitator payments '
            'the log path missed, the gap is reported; if the two disagree on the payments both see, nothing is published.</p></figure>')


def ladder():
    rows = "".join(f'<li><b>{w}</b><span>{q}</span><em>{no}</em></li>' for w, q, no in RULES)
    return (f'<figure class="figure diagram-html"><ol class="ladder">{rows}'
            '<li class="kept"><b>Kept</b><span>Yes to every question: adjusted volume</span><em></em></li></ol>'
            '<p class="gate">A payment leaves at the first question it fails, so each bar of the waterfall means one thing. '
            'Payments under 1 cent are reported, never removed.</p></figure>')


SLICES = [("S1 One hour, one number", 3, "done 2026-10-27"), ("S2 Attribution and cross-check", 6, "due 2026-11-10"),
          ("S3 7-day keyless census", 4, "due 2026-11-10"), ("S4 Rules and README Results", 6, "due 2026-11-10"),
          ("S5 Site", 5, "due 2026-11-17"), ("S6 Visa/Artemis PDF method", 2, "due 2026-11-17")]


def slices():
    rows = "".join(
        f'<div class="row"><span>{n}</span><div class="track"><div class="bar {"kept" if "done" in d else "w0" if "11-10" in d else "hop"}" '
        f'style="left:0;width:{100 * h / 6:.1f}%"></div></div><span class="value">{h} h</span><span class="due">{d}</span></div>'
        for n, h, d in SLICES)
    return (f'<figure class="figure bridge slices"><h3>Slice 1 is done; slices 2–4 need 16 more hours before November 10</h3>{rows}'
            '<p class="sources">Hours are estimates; the Cantina contest takes hours until November 3. The highlighted bar is done; the lighter bars fall after November 10.</p></figure>')


def prd_html():
    parts = [(ROOT / f"docs/prd/{n}").read_text() for n in ("1-product.md", "2-evidence.md", "3-build.md")]
    first = parts[0].split("\n---\n", 1)[1].split("\nContinued in")[0]
    text = "\n\n".join([first] + [part[part.index("\n## "):] for part in parts[1:]])
    drawn = iter([flow(), ladder(), slices()])
    text = re.sub(r"```mermaid\n.*?```", lambda _: f"\n\n{next(drawn)}\n\n", text, flags=re.S)
    return md(text)


def review_html():
    r1 = json.loads((ROOT / "review/round-1.json").read_text())
    fix = {x["id"]: x for x in json.loads((ROOT / "review/round-1-repair.json").read_text())["responses"]}
    ver = {x["id"]: x for x in json.loads((ROOT / "review/round-1-verify.json").read_text())["results"]}
    rows = "".join(
        f"<tr><td>{f['id']}</td><td>{f['severity']}</td><td>{html.escape(f['claim'])}</td>"
        f"<td>{html.escape(fix[f['id']]['where'])}</td><td>{ver[f['id']]['verdict']}</td></tr>"
        for f in r1["findings"])
    return ("<table><thead><tr><th>#</th><th>Severity</th><th>Finding</th><th>Where it was fixed</th>"
            f"<th>Verifier</th></tr></thead><tbody>{rows}</tbody></table>")


def bridge(hour):
    w0, w1 = hour["w0_visible"]["usdc"], hour["w1"]["usdc"]
    hop = w0 - w1
    pct = lambda v: f"{100 * v / w0:.2f}%"
    row = lambda label, cls, left, width, value: (
        f'<div class="row"><span>{label}</span><div class="track"><div class="bar {cls}" '
        f'style="left:{left};width:{width}"></div></div><span class="value">{value}</span></div>')
    return f"""<figure class="figure bridge" aria-labelledby="bridge-title">
<h3 id="bridge-title">In this hour, a fifth of what x402scan's filter counted was a payment moving a second time</h3>
{row("x402scan's filter (W0)", "w0", "0", "100%", f"${w0:,.2f}")}
{row("Second hops of routed payments", "hop", pct(w1), pct(hop), f"−${hop:,.2f}")}
{row("Payments (W1)", "kept", "0", pct(w1), f"${w1:,.2f}")}
<p class="sources">One hour only: {hour['hour_start_utc'][:10]} 14:00–15:00 UTC, Base blocks {hour['first_block']:,}–{hour['last_block']:,}.
Not a 7-day rate. Second hops: 444 router hops of $0.001 and 4 forwards of about $30. Source: out/s1/hour.json.</p>
</figure>"""


def main():
    hour = json.loads((ROOT / "out/s1/hour.json").read_text())
    cap = json.loads((ROOT / "out/reconcile/x402scan-capture.json").read_text())
    s1 = (ROOT / "docs/slices/s1.md").read_text().split("\n", 1)[1]
    body = f"""<a class="skip" href="#main">Skip to content</a><div class="page plan">
<header class="site-header"><a class="brand" href="#main">Rahil Bhavan</a>
<nav class="nav" aria-label="Sections"><a href="#case">Case</a><a href="#prd">Plan</a><a href="#review">Review</a><a href="#slice1">First hour</a></nav></header>
<main id="main">
<p class="notice">Draft plan, not published. The only measured result so far is one hour of Base blocks.</p>
<section class="site-hero"><div><h1>x402 ground truth</h1>
<p>How much of the x402 payment volume on Base is real payments? Published figures disagree by about a hundred times,
and none of the adjusted ones can be rerun. This is the plan to measure it with rules anyone can rerun, and the first hour of data.</p>
<p class="status">x402scan, Base, 7 days to {cap['captured_at'][:10]}: ${cap['usdc']:,.0f} across {cap['stats']['total_transactions']:,} transactions (captured, not yet checked)</p></div>
<div class="featured">{bridge(hour)}</div></section>
<section class="story" id="case"><h2>The project as a case</h2>
<dl class="case-facts">
<div><dt>Problem</dt><dd>x402 adoption numbers range from about $120k to $15M, from different windows, chains and filters. An analyst can't tell how much of the gap is method.</dd></div>
<div><dt>Decision</dt><dd>Reproduce x402scan's counting filter exactly (W0), then subtract five named rules (W1–W5), each a tested function with its own count and examples.</dd></div>
<div><dt>Artifact</dt><dd>So far, this plan, a red-team record and a deterministic one-hour pull. The 7-day waterfall is slice 3.</dd></div>
<div><dt>Verification</dt><dd>Two runs from an empty cache gave byte-identical files; 5 payments matched on a second RPC provider; 10 review findings fixed and confirmed.</dd></div>
<div><dt>Next test</dt><dd>Slice 2: count batch settlement, scan every block in one hour for facilitator transactions the log path misses, and bound the rest with nonces.</dd></div>
</dl>
<p class="waiting"><strong>Waiting on Rahil.</strong> Is any line of the plan wrong? Open calls: addresses on public pages (hashes only until answered), an optional census key, and creating the repo, site and any post.</p></section>
<section class="story" id="prd"><h2>The plan</h2>{prd_html()}</section>
<section class="story" id="review"><h2>Red-team review, round 1</h2>
<p>A fresh reviewer found 10 problems. Each was repaired once, and a separate reviewer confirmed all 10 fixes in the text.</p>
{review_html()}</section>
<section class="story" id="slice1"><h2>Slice 1: one hour, one number</h2>{md(s1)}</section>
</main>
<footer class="footer">rahil-design {(BUNDLE / "VERSION").read_text().strip()} · Design review pending · Built from docs/prd/, review/ and out/s1/</footer>
</div>"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(document("x402 ground truth: plan and first hour", body, extra_css=CSS))
    print(OUT)


if __name__ == "__main__":
    main()
