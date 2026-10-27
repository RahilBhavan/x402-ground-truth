# x402 ground truth

**One sentence.** A payments analyst at Coinbase or Circle can see how much of x402's reported Base volume survives each named exclusion rule, so that they can quote an adoption number with its method attached.
**Owner.** Rahil Bhavan
**Date.** 2026-10-27
**Status.** DRAFT
**Path.** `docs/prd/` (three parts) in `~/projects/x402-ground-truth` (local; no remote yet)

---

## 1. Who it is for

**Role.** A product, BD or data analyst on an agent-payments team (Coinbase Developer Platform's x402 team, Circle's USDC payments team) who has to put an x402 adoption number in a deck or a post. The secondary reader is a crypto journalist or researcher who quotes x402 numbers.
**How many.** Day one: about 10 readers (Rahil, the reviewers he chooses, and the recruiters who open the repo).
**Where they are.** At a desk, comparing a dashboard number with a number from an X thread.
**What they already have.** A browser, a Basescan account at most, no node or paid data plan.

## 2. Today, without this

The analyst picks one of these figures and quotes it: x402scan's live total, the Visa/Artemis "adjusted" figure, an X thread's 30-day number, or a news summary's payment count. The published figures disagree by about two orders of magnitude, but they cover different windows and chains (see Facts), so nobody can tell how much of the gap is method. x402scan publishes its counting filter as code, but no exclusion rules. The adjusted figures (Visa/Artemis, Artemis) publish no code. The analyst cannot rerun any adjusted figure on the same blocks.

## 3. Must do

1. Read every x402 "exact"-scheme USDC settlement on Base inside one fixed block range from public chain data.
2. Attribute each settlement to a facilitator from a versioned, cited address list.
3. Apply each exclusion rule as a separate, named and versioned function, and report how much volume and how many payments each one removes, in order.
4. Show each published figure next to this project's number for the same window, with that figure's definition and date.
5. Publish the settlement table, rule outputs and a single rerun command that reproduces every published number from the pinned block range.
6. Give five example transactions for each rule, each linked to Basescan, so a reader can check the rule by hand.

## 4. Non-goals

- No live or real-time dashboard. One pinned window, rerun on demand. x402scan already does live totals.
- No list of wallets accused of wash trading. Rules describe patterns, and examples show transactions, not named people or companies.
- No chains other than Base in v1. Solana x402 traffic waits for a separate version.
- No payment product, facilitator or spend-policy layer. That was idea #1+#6 and is a separate project.
- No change to `x402-exception-desk`. It gets one README link after this ships.
- No MPP/Tempo pipeline unless slice 1 shows its data can be read for free in under one day of work (cut list item 1).

## 5. Assumed decisions

- `ASSUMED 2026-10-27` A new repo, not a module inside `x402-exception-desk`. Rules out one combined repo, because that repo is a finished v1.1 release that answers a different question with synthetic data.
- `DECIDED 2026-10-27` (Rahil, 2026-10-27: "Why does this not use my design skills") The project site, diagrams and any X card use `rahil-design` (charcoal, white and yellow, Anton and IBM Plex Sans, figures on the light figure surface). Rules out reusing `x402-exception-desk`'s blue report look.
- `ASSUMED 2026-10-27` The window is the 47 complete 3.5-hour buckets of x402scan's 7-day Base series captured on 2026-10-27, from 2026-10-20 18:00 to 2026-10-27 14:30 UTC (164.5 hours), on Base only. Rules out a 30-day or all-time headline in v1, and the rolling total's unknown start (see the change log).

## 6. Open questions

1. May the rule example pages show payer and payee addresses (public onchain data), or only transaction hashes? Asked of: Rahil. Waiting on it: the rules page in slice 5. The default until answered is hashes only.
2. Optional speed-up: a free CDP API key or a Google Cloud project for BigQuery's public Base dataset (both account actions) would replace the overnight keyless pull. Asked of: Rahil. Waiting on it: nothing; every slice runs keyless.
3. Creating the public GitHub repo, the GitHub Pages site and any X post are Rahil's actions. Waiting on it: publication only. All building happens locally.

## 7. Constraints

**Deadline.** 2026-11-10 for slices S1–S4 and the README Results; the site (S5) follows by 2026-11-17. Two weeks, because the scan's "why now" (agent-payment numbers being argued this week) loses value as the argument moves on. The Cantina v4lend contest ends 2026-11-03 and competes for the same hours.
**Must use.** Python 3.12 standard library plus SQLite, matching `x402-exception-desk`. Only free, keyless or free-tier public data.
**Must not touch.** `x402-exception-desk`, any wallet or key, any paid API.
**People.** Rahil, about 10 hours a week, with agents: about 20 hours to 2026-11-10, fewer in the Cantina week. Slices are estimated in hours to fit that.
**Legal or policy.** Public onchain data only. No claim that a named person or company committed fraud.

Continued in [2-evidence.md](2-evidence.md) and [3-build.md](3-build.md).
