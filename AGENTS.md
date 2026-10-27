# x402 ground truth: agent rules

How much of x402's reported Base volume survives named, rerunnable exclusion rules. The plan is `docs/prd/` (three parts). Build only what it names; new requests go to its change log first.

## Commands

```sh
python3 -m unittest discover -s tests        # behaviour tests, offline (fake RPC)
python3 -m ground_truth capture --days 7     # x402scan rolling Base figure (free tRPC route, never the paid /api/x402)
python3 -m ground_truth hour                 # slice 1: one hour of Base blocks, keyless
python3 /home/rahil/.t3/projects/main/.agents/skills/prd-loop/scripts/check_prd.py docs/prd/*.md --sources research/sources*.md
uv run --with markdown python scripts/plan_page.py   # build/plan.html in rahil-design
```

## Rules

- **Build loop.** One slice of `docs/prd/3-build.md` per branch and PR, delivered with the hub's `full-send` skill (or `full-stop` when Rahil has not asked for merging): failing test first, real-data proof, one independent review, at most one repair, CI green, then merge. Record proof in `docs/slices/sN.md`.
- **Proof is a real run.** Unit tests use fixtures and a fake RPC. A slice is done only when its real-data command has run and its numbers are in `docs/slices/`. Determinism checks rerun from an empty cache.
- **Data.** Public onchain data and free keyless endpoints only. No paid API, no account, no key unless Rahil supplies one.
- **Privacy.** Payer and payee addresses never appear in `site/` or any public page (PRD open question 1). Contract and facilitator addresses may.
- **Design.** Every page, diagram and chart uses `rahil-design` from the first draft: its `render_markup.document()`, tokens and `chart_theme`. Run its `design_check.py lint` and `pixel_audit.py`. A visual stays design review pending until Rahil passes it with `review_record.py`, and a pending visual is a merge blocker under full-send. Never borrow another repo's look.
- **External actions.** Making the repo public, publishing the site and posting about results are Rahil's actions. Never post, message or open issues elsewhere.
- **Files.** The pre-commit hook rejects files over 5,000 tokens and runs the rahil-design guard. Enable it with `git config core.hooksPath .githooks`. Do not bypass it.
- **Generated data.** `out/` and `build/` are ignored. Commit summaries in `docs/slices/`, never raw caches.
