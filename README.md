# x402 ground truth

How much of the x402 payment volume on Base survives named, rerunnable exclusion rules. One pinned window: the 47 complete 3.5-hour buckets of x402scan's 7-day Base series, 2026-10-20 18:00 to 2026-10-27 14:30 UTC, Base blocks 52,864,927 to 53,161,026.

## Results

Of $386,106.22 that x402scan's method counts on Base in this window, $44,690.08 passes all five rules: 11.57% of the dollars.

| Step | Payments left | USDC left | From |
| --- | --- | --- | --- |
| W0, x402scan's filter | 705,466 | $386,106.22 | `out/waterfall.json` |
| W1, one row per x402 payment | 705,390 | $386,146.33 | `out/waterfall.json` |
| W2, self-payment removed | 704,524 | $385,996.36 | `out/waterfall.json` |
| W3, round trip removed | 695,095 | $382,373.48 | `out/waterfall.json` |
| W4, thin seller removed | 673,144 | $47,215.31 | `out/waterfall.json` |
| W5, farming burst removed | 444,768 | $44,690.08 | `out/waterfall.json` |

- **One pair decides the headline.** Four payments from one wallet to one other wallet carry $329,000.00, 85.21% of W0's dollars (`out/settlements.sqlite`, `payments` table; checked on chain in [docs/slices/s4.md](docs/slices/s4.md)). W4 removes them because the payee had one payer. Without them, the rules keep 78.20% of W1's dollars (`out/waterfall.json`).
- **The published share holds, on a different window.** 11.57% kept is within the pre-registered 5 points of the Visa/Artemis 11.05% (since launch, all chains). The two windows differ, and the match rests on those four payments.
- **Farming is many payments, few dollars.** W5 removes 228,376 payments, 32.38% of W1's count, but $2,525.24 (`out/waterfall.json`).
- **The result moves with one threshold.** With W4's distinct-payer floor halved to 1, $377,022.40 is kept; doubled to 4, $40,146.61 (`out/sensitivity.csv`).
- **Replication.** W0 is 1.0009 times x402scan's own $385,770.37 for the same 47 buckets (`out/reconcile/x402scan.csv`).

Rules are patterns, not accusations. Pages show transaction hashes, never wallet addresses. Five example transactions per rule are in `out/examples/`.

Pinned run: `out/waterfall.json` SHA-256 `f91e9d15a62af5fe7d42ec3bf10e4e4c23b3c8a0166ce757ec63348f85ee22e0`. The thresholds were fixed in [docs/preregistration.md](docs/preregistration.md) before the census ran; its wording was made exact on 2026-10-28, before any W2–W5 result existed.

## Rerun

```sh
python3 -m ground_truth capture --days 7     # x402scan's rolling Base figure (free page route)
python3 -m ground_truth run --buckets out/reconcile/x402scan-buckets-2026-10-27T173936Z.json
python3 scripts/check_examples.py            # every example hash has a successful receipt
python3 -m unittest discover -s tests
```

Python 3.12 standard library and SQLite. Public onchain data through keyless nodes; no key, no paid API.

## Site

Three static pages (answer, rules, method) built from the run in rahil-design. They are not published, and design review is pending.

```sh
python3 -m ground_truth.figure     # the exhibit, from the run (needs Proof Desk and uv)
python3 -m ground_truth.site       # site/ (generated, not in Git)
python3 scripts/check_site.py      # headline, figure, no wallet address on any page
```

## Documents

- Plan: [docs/prd/](docs/prd/) (three parts; DRAFT until Rahil approves)
- Slices: [docs/slices/](docs/slices/)
- Sources: [research/sources.md](research/sources.md), [research/sources-observed.md](research/sources-observed.md)
