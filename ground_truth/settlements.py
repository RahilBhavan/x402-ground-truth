"""Rule W1 on one facilitator-sent transaction: which USDC transfers are x402 payments, and why the rest are not.

classify() is pure: a receipt, its sender, the facilitator list and known batch channels in; rows out.
"""
from collections import Counter

from .constants import (PROXIES, SECOND_HOP_SHARE, TOPIC_AUTHORIZATION_USED, TOPIC_BATCH_CLAIMED, TOPIC_PROXY_SETTLED,
                        TOPIC_PROXY_SETTLED_PERMIT, TOPIC_TRANSFER, USDC)

BATCH = PROXIES["batch_settlement"]
PERMIT_PROXIES = {PROXIES["exact_proxy"]: "exact_proxy", PROXIES["upto"]: "upto"}


def addr(topic):
    return "0x" + topic[-40:].lower()


def _transfers(receipt):
    return [{"log_index": int(l["logIndex"], 16), "payer": addr(l["topics"][1]), "payee": addr(l["topics"][2]),
             "atomic": int(l["data"], 16)}
            for l in receipt["logs"] if l["address"].lower() == USDC and l["topics"][0] == TOPIC_TRANSFER]


def _is_second_hop(t, earlier):
    """A transfer out of an address that received at least SECOND_HOP_SHARE of this amount earlier in the tx."""
    return any(e["payee"] == t["payer"] and e["log_index"] < t["log_index"]
               and SECOND_HOP_SHARE * e["atomic"] <= t["atomic"] <= e["atomic"] for e in earlier)


def classify(receipt, sender, facilitators, channels):
    """None if outside W0. Otherwise {"w0": transfers, "payments": rows, "removed": rows with a reason}."""
    sender = sender.lower()
    if sender not in facilitators:
        return None
    tx, logs = receipt["transactionHash"], receipt["logs"]
    transfers = _transfers(receipt)
    authorizers = Counter(addr(l["topics"][1]) for l in logs
                          if l["address"].lower() == USDC and l["topics"][0] == TOPIC_AUTHORIZATION_USED)
    proxy_scheme = next((PERMIT_PROXIES[l["address"].lower()] for l in logs if l["address"].lower() in PERMIT_PROXIES
                         and l["topics"][0] in (TOPIC_PROXY_SETTLED, TOPIC_PROXY_SETTLED_PERMIT)), None)
    base = {"tx": tx, "facilitator": facilitators[sender]["facilitator"]}
    payments, removed, kept = [], [], []

    for t in transfers:
        if authorizers[t["payer"]] > 0:
            authorizers[t["payer"]] -= 1
            payments.append({**base, **t, "scheme": "eip3009"})
            kept.append(t)
        elif BATCH in (t["payer"], t["payee"]):
            removed.append({**base, **t, "reason": "channel_movement"})
        elif _is_second_hop(t, kept + [r for r in removed if r["reason"] != "non_payment"]):
            removed.append({**base, **t, "reason": "second_hop"})
        elif proxy_scheme and t["payer"] not in PROXIES.values() and t["payee"] not in PROXIES.values():
            payments.append({**base, **t, "scheme": proxy_scheme})
            kept.append(t)
        else:
            removed.append({**base, **t, "reason": "non_payment"})

    for l in logs:  # batch claims move no USDC: the payment is the claimed voucher amount
        if l["address"].lower() == BATCH and l["topics"][0] == TOPIC_BATCH_CLAIMED:
            channel = channels.get(l["topics"][1].lower(), {"payer": "unknown", "receiver": "unknown"})
            payments.append({**base, "log_index": int(l["logIndex"], 16), "payer": channel["payer"],
                             "payee": channel["receiver"], "atomic": int(l["data"][2:66], 16),
                             "scheme": "batch_settlement"})
    payments.sort(key=lambda p: p["log_index"])
    return {"w0": [{**base, **t} for t in transfers], "payments": payments, "removed": removed}
