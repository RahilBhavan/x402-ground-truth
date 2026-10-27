# x402 ground truth: observed sources

Rows observed during review and the build. Desk research is in [sources.md](sources.md).

## R. Observed by the red-team reviewer, 2026-10-27 (review/round-1.json)
| # | Claim | Source | Publisher | Date | Type | Conf |
|---|---|---|---|---|---|---|
| R1 | Deployed `x402ExactPermit2Proxy.sol` emits `Settled()` / `SettledWithPermit()`; `x402PermitTransfer` exists only in the spec text. Base proxies: exact 0x402085c248EeA27D92E8b30b2C58ed07f9E20001, upto 0x4020A4f3b7b90ccA423B9fabCc0CE57C6C240002, batch 0x4020074e9dF2ce1deE5A9C1b5c3f541D02a10003. Logs over blocks 53124928-53164928: 5 / 4,495 / 617. | https://github.com/x402-foundation/x402/tree/main/contracts/evm ; eth_getLogs on base-rpc.publicnode.com | x402 Foundation / Obs | 2026-10-27 | Primary (Obs) | H |
| R2 | x402scan API routes are paid (`.paid('0.01')`) and accept lookbacks of 1, 7, 14 or 30 days only; the network chart uses 48 buckets. | https://github.com/Merit-Systems/x402scan (apps/scan/src/app/api/x402/_lib/schemas.ts, types/timeframes.ts) | Merit Systems | 2026-10-27 | Primary | H |
| R4 | x402scan's Base CDP syncer is `enabled: false`; Bitquery is enabled with cutover 2026-06-09T18:00Z. HEAD 5732bb83c8c4290f413f24318a838e3fee4ed2bf. | sync/transfers/trigger/chains/evm/base/{cdp,bitquery}/config.ts | Merit Systems | 2026-10-27 | Primary | H |
| R8 | Sizing inference: G6's at most ~290k all-caller AuthorizationUsed per day bounds a 7-day pull at ~2M logs. | inference from G6, G2 | - | 2026-10-27 | Inference | M |

## O. Slice 2 observations, 2026-10-27
| # | Claim | Source | Publisher | Date | Type | Conf |
|---|---|---|---|---|---|---|
| O1 | x402scan's 7-day stats come from materialized views `stats_aggregated_7d` / `stats_buckets_7d` filtered `block_timestamp >= NOW() - INTERVAL '7 days'`; buckets are `time_bucket('3 hours 30 minutes')`. Refresh job not in the repo. | packages/internal/databases/transfers/prisma/migrations/20251111231947_overall_7d_mv/migration.sql at 5732bb83 | Merit Systems | 2026-10-27 | Primary | H |
| O2 | Captured bucketed 7d Base series: 49 buckets 2026-10-20T14:30Z to 2026-10-27T14:30Z, sum $387,235.86 vs overall $387,236.51. | out/reconcile/x402scan-buckets-*.json (free tRPC `public.stats.bucketed`) | Obs | 2026-10-27 | Primary (Obs) | H |
| O3 | x402BatchSettlement emits Claimed(channelId, sender, claimAmount, newTotalClaimed) on claim and Settled(receiver, token, sender, amount) on payout; deposits emit Deposited. | x402-foundation/x402 contracts/evm/src/x402BatchSettlement.sol at dbe1080a | x402 Foundation | 2026-10-27 | Primary | H |
| O4 | base-rpc.publicnode.com: eth_getLogs max 50,000 blocks per call; ranges ~3M+ blocks back or old-state calls (eth_getCode at block 26,000,000) return HTTP 403; logs 2M blocks back still served. | Obs | - | 2026-10-27 | Obs | H |
