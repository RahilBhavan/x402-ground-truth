# Pre-registration

Written 2026-10-27, before the 7-day census (slice 3) has run. Each falsifier and every rule threshold is fixed here. A later change needs a dated row below saying why, and the README must show both the old and the new result.

## The window

The 7 days ending at the x402scan capture in `out/reconcile/x402scan-capture.json` (captured 2026-10-27; latest block time 2026-10-27T16:35:47Z), Base only.

## Falsifiers

1. **No wash story.** If W2–W5 together remove less than 5% of W1 dollars, the headline says that the published "fake traffic" story does not hold on this window.
2. **The published share holds.** If the share of W0 dollars kept lands within 5 percentage points of the relayed Visa/Artemis share (about 11% of dollars kept, source D3), the headline is "the published adjusted share holds on a later window", labelled as a different window.
3. **Replication.** If W0 differs from x402scan's captured 7-day Base figure by more than 5% after the hour coverage correction (AC-5), the replication is wrong. Rule results are then reported only as shares, and the README says so.

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
