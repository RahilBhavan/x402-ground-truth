"""Logs -> senders -> facilitator receipts -> W0/W1 rows, for any block range."""
from collections import Counter

from . import channels as channel_lookup
from .constants import PROXIES, TOPIC_AUTHORIZATION_USED, TOPIC_BATCH_CLAIMED, USDC
from .settlements import classify

CHUNK = 300  # blocks per eth_getLogs; ~2,000 AuthorizationUsed logs per chunk, well under the 20,000 cap
RPC_BATCH = 50  # calls per JSON-RPC batch request


def logs(rpc, address, topic0, first, last):
    out = []
    for a in range(first, last + 1, CHUNK):
        b = min(a + CHUNK - 1, last)
        f = {"address": address, "fromBlock": hex(a), "toBlock": hex(b)}
        if topic0:
            f["topics"] = [topic0]
        out += rpc.call("eth_getLogs", [f], label=f"logs {address[:10]} {a}-{b}")
    return out


def batched(rpc, method, hashes):
    out = []
    for i in range(0, len(hashes), RPC_BATCH):
        out += rpc.batch([(method, [h]) for h in hashes[i:i + RPC_BATCH]], label=f"{method} x{len(hashes[i:i + RPC_BATCH])}")
    return out


def collect(rpc, first, last, facilitators):
    marker_logs = logs(rpc, USDC, TOPIC_AUTHORIZATION_USED, first, last)
    proxy_logs = {k: logs(rpc, a, None, first, last) for k, a in PROXIES.items()}
    hashes = sorted({l["transactionHash"] for l in marker_logs} |
                    {l["transactionHash"] for v in proxy_logs.values() for l in v})
    sender = {t["hash"]: t["from"].lower() for t in batched(rpc, "eth_getTransactionByHash", hashes)}
    fac_hashes = sorted(h for h in hashes if sender[h] in facilitators)
    receipts = batched(rpc, "eth_getTransactionReceipt", fac_hashes)
    claim_ids = {l["topics"][1].lower() for l in proxy_logs["batch_settlement"] if l["topics"][0] == TOPIC_BATCH_CLAIMED}
    channels = channel_lookup.lookup(rpc, claim_ids, last)
    rows = {"transfers": [], "w0": [], "payments": [], "removed": []}
    for r in receipts:
        out = classify(r, sender[r["transactionHash"]], facilitators, channels)
        for k in rows:
            rows[k] += out[k]
    for k in rows:
        rows[k].sort(key=lambda x: (x["tx"], x["log_index"]))
    claim_senders = Counter("facilitator" if sender[l["transactionHash"]] in facilitators else "other"
                            for l in proxy_logs["batch_settlement"] if l["topics"][0] == TOPIC_BATCH_CLAIMED)
    meta = {"authorization_used_logs_all_callers": len(marker_logs),
            "proxy_logs": {k: len(v) for k, v in proxy_logs.items()},
            "marker_txs": len(hashes), "marker_txs_sent_by_facilitators": len(fac_hashes),
            "batch_claims_by_sender": dict(sorted(claim_senders.items())),
            "batch_channels_resolved": f"{len(channels)}/{len(claim_ids)}"}
    return rows, fac_hashes, meta
