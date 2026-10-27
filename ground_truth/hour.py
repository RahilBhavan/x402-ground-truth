"""Slice 1: x402 settlement through listed facilitators in one hour of Base blocks."""
import calendar
import json
import time
from collections import Counter

from . import facilitators
from .constants import (DUST_ATOMIC, PROXIES, TOPIC_AUTHORIZATION_USED, TOPIC_TRANSFER, USDC,
                        X402SCAN_COMMIT)

CHUNK = 300  # blocks per eth_getLogs; ~2,000 AuthorizationUsed logs, well under the 20,000 cap
BATCH = 50


def block_at(rpc, ts):
    """First block with timestamp >= ts, by binary search around a 2-second-block estimate."""
    ts_of = lambda n: int(rpc.call("eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)
    head = rpc.call("eth_getBlockByNumber", ["latest", False], cache=False)
    guess = int(head["number"], 16) - (int(head["timestamp"], 16) - ts) // 2
    lo, hi = guess - 2000, guess + 2000
    if not ts_of(lo) < ts <= ts_of(hi):
        raise RuntimeError(f"block estimate for {ts} is off by more than 2,000 blocks")
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if ts_of(mid) < ts else (lo, mid)
    return hi


def logs(rpc, address, topic0, first, last):
    out = []
    for a in range(first, last + 1, CHUNK):
        b = min(a + CHUNK - 1, last)
        f = {"address": address, "fromBlock": hex(a), "toBlock": hex(b)}
        if topic0:
            f["topics"] = [topic0]
        out += rpc.call("eth_getLogs", [f])
    return out


def batched(rpc, method, hashes):
    out = []
    for i in range(0, len(hashes), BATCH):
        out += rpc.batch([(method, [h]) for h in hashes[i:i + BATCH]])
    return out


def addr(topic):
    return "0x" + topic[-40:]


def run(rpc, start_iso):
    start = calendar.timegm(time.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ"))
    first, last = block_at(rpc, start), block_at(rpc, start + 3600) - 1
    fac = facilitators.load()

    decimals = int(rpc.call("eth_call", [{"to": USDC, "data": "0x313ce567"}, "latest"]), 16)
    marker_logs = logs(rpc, USDC, TOPIC_AUTHORIZATION_USED, first, last)
    proxy_logs = {k: logs(rpc, a, None, first, last) for k, a in PROXIES.items()}

    tx_hashes = sorted({l["transactionHash"] for l in marker_logs} |
                       {l["transactionHash"] for v in proxy_logs.values() for l in v})
    txs = batched(rpc, "eth_getTransactionByHash", tx_hashes)
    sender = {t["hash"]: t["from"].lower() for t in txs}
    fac_hashes = sorted(h for h in tx_hashes if sender[h] in fac)
    receipts = batched(rpc, "eth_getTransactionReceipt", fac_hashes)

    proxy_of = {a: k for k, a in PROXIES.items()}
    w0_atomic = w0_count = 0
    payments = []  # one row per x402 payment that passes W1
    for r in receipts:
        h = r["transactionHash"]
        usdc_transfers = [l for l in r["logs"] if l["address"].lower() == USDC and l["topics"][0] == TOPIC_TRANSFER]
        w0_count += len(usdc_transfers)
        w0_atomic += sum(int(l["data"], 16) for l in usdc_transfers)
        authorizers = Counter(addr(l["topics"][1]) for l in r["logs"]
                              if l["address"].lower() == USDC and l["topics"][0] == TOPIC_AUTHORIZATION_USED)
        schemes = {proxy_of[l["address"].lower()] for l in r["logs"] if l["address"].lower() in proxy_of}
        for l in usdc_transfers:
            payer, payee = addr(l["topics"][1]), addr(l["topics"][2])
            if authorizers[payer] > 0:
                authorizers[payer] -= 1
                scheme = "eip3009"
            elif schemes and payer not in PROXIES.values() and payee not in PROXIES.values():
                scheme = sorted(schemes)[0]
            else:
                continue
            payments.append({"tx": h, "log_index": int(l["logIndex"], 16), "scheme": scheme,
                             "payer": payer, "payee": payee, "atomic": int(l["data"], 16),
                             "facilitator": fac[sender[h]]["facilitator"]})

    payments.sort(key=lambda p: (p["tx"], p["log_index"]))
    w1_atomic = sum(p["atomic"] for p in payments)
    dust = [p for p in payments if p["atomic"] < DUST_ATOMIC]
    by = lambda key: {k: {"payments": sum(1 for p in payments if p[key] == k),
                          "usdc": sum(p["atomic"] for p in payments if p[key] == k) / 10 ** decimals}
                      for k in sorted({p[key] for p in payments})}
    return {
        "hour_start_utc": start_iso, "first_block": first, "last_block": last,
        "x402scan_commit": X402SCAN_COMMIT, "usdc_decimals": decimals,
        "authorization_used_logs_all_callers": len(marker_logs),
        "proxy_logs": {k: len(v) for k, v in proxy_logs.items()},
        "marker_txs": len(tx_hashes), "marker_txs_sent_by_facilitators": len(fac_hashes),
        "w0_visible": {"transfers": w0_count, "usdc": w0_atomic / 10 ** decimals,
                       "note": "USDC Transfers in facilitator-sent txs that carry an x402 marker; "
                               "facilitator txs without a marker are counted in slice 2"},
        "w1": {"payments": len(payments), "usdc": w1_atomic / 10 ** decimals},
        "dust_under_1_cent": {"payments": len(dust), "share_of_payments": round(len(dust) / max(len(payments), 1), 4),
                              "usdc": sum(p["atomic"] for p in dust) / 10 ** decimals},
        "by_scheme": by("scheme"), "by_facilitator": by("facilitator"),
        "check_by_hand": [p["tx"] for p in payments[:: max(len(payments) // 5, 1)][:5]],
    }, payments


def write(result, payments, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hour.json").write_text(json.dumps(result, indent=1, sort_keys=True))
    (out_dir / "hour-payments.jsonl").write_text("".join(json.dumps(p, sort_keys=True) + "\n" for p in payments))
