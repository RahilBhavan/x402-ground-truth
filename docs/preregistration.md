# Pre-registration

Written 2026-10-27, before the 7-day census (slice 3) has run. Each falsifier and every rule threshold is fixed here. A later change needs a dated row below saying why, and the README must show both the old and the new result.

## The window

The 47 complete 3.5-hour buckets of x402scan's bucketed 7-day Base series, captured 2026-10-27 (`out/reconcile/x402scan-buckets-*.json`): 2026-10-20 18:00 to 2026-10-27 14:30 UTC, 164.5 hours, Base only.

## Falsifiers

1. **No wash story.** If W2–W5 together remove less than 5% of W1 dollars, the headline says that the published "fake traffic" story does not hold on this window.
2. **The published share holds.** If the share of W0 dollars kept lands within 5 percentage points of the relayed Visa/Artemis share (about 11% of dollars kept, source D3), the headline is "the published adjusted share holds on a later window", labelled as a different window.
3. **Replication.** If W0 summed over the 47 buckets differs from x402scan's sum of the same buckets by more than 5% after the hour coverage correction (AC-5), the replication is wrong. Rule results are then reported only as shares, and the README says so.

## Rule thresholds (defaults; sensitivity at 0.5x and 2x)

| Rule | Removes a payment when | Default |
| --- | --- | --- |
| W1 second hop | a transfer leaves an address that received it earlier in the same transaction, at 90% to 100% of the amount received | 90% |
| W2 | payer = payee | — |
| W3 | the payee sends at least this share of the payment back to the payer within 24 hours, in any transaction | 90% |
| W4 | the payee has fewer than 3 surviving payments, or fewer than 2 distinct payers, in the window | 3 payments, 2 payers |
| W5 | the payer–payee pair made at least this many payments of one identical amount in one UTC day | 1,000 |

Dust (under $0.01) is reported for every rule and never removed.

## Changes

| Date | Change | Why |
| --- | --- | --- |
| 2026-10-27 | Window changed from "7 days ending at the capture" to the 47 complete x402scan buckets, before the census ran | x402scan's rolling total starts at an unpublished refresh time; the buckets have exact bounds (slice 2 finding 1) |
| 2026-10-27 | W0 now applies x402scan's pass-through collapse and includes facilitator-sent transactions with no x402 marker; W1 removes those as `unmarked`. Made after the first census bucket was seen (W0 13.7% over x402scan) and before the other 46 ran. No threshold changed | x402scan's code does both (sources O6, O7); without them W0 is not x402scan's filter |
