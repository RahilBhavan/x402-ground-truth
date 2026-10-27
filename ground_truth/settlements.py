"""Rule W1 on one facilitator-sent transaction: which USDC transfers are x402 payments, and why the rest are not.

classify() is pure: a receipt, its sender, the facilitator list and known batch channels in; rows out.
A payment is counted once, at the payer's own transfer. When the money is forwarded inside the transaction,
the payment's payee becomes the final recipient and `via` names the first address it passed through.
"""
from collections import Counter

from .constants import (BATCH_CONTRACT, PROXIES, SECOND_HOP_SHARE, TOPIC_AUTHORIZATION_USED, TOPIC_BATCH_CLAIMED,
                        TOPIC_PROXY_SETTLED, TOPIC_PROXY_SETTLED_PERMIT, TOPIC_TRANSFER, USDC)

PERMIT_PROXIES = {PROXIES["exact_proxy"]: "exact_proxy", PROXIES["upto"]: "upto"}
CONTRACTS = set(PROXIES.values())
REASONS = ("non_payment", "second_hop", "channel_movement")


def addr(topic):
    return "0x" + topic[-40:].lower()


def _from(log, address, topic0):
    return log["address"].lower() == address and log["topics"][0] == topic0


def _transfers(logs):
    return [{"log_index": int(l["logIndex"], 16), "payer": addr(l["topics"][1]), "payee": addr(l["topics"][2]),
             "atomic": int(l["data"], 16)} for l in logs if _from(l, USDC, TOPIC_TRANSFER)]


def classify(receipt, sender, facilitators, channels):
    """None if outside W0. Otherwise {"w0": transfers, "payments": rows, "removed": rows with a reason in REASONS}."""
    sender = sender.lower()
    if sender not in facilitators:
        return None
    logs = receipt["logs"]
    base = {"tx": receipt["transactionHash"], "facilitator": facilitators[sender]["facilitator"]}
    authorizers = Counter(addr(l["topics"][1]) for l in logs if _from(l, USDC, TOPIC_AUTHORIZATION_USED))
    settles = [PERMIT_PROXIES[l["address"].lower()] for l in logs if l["address"].lower() in PERMIT_PROXIES
               and l["topics"][0] in (TOPIC_PROXY_SETTLED, TOPIC_PROXY_SETTLED_PERMIT)]
    transfers = _transfers(logs)
    payments, removed = [], []
    holder = {}  # address -> (payment, amount it received), for following a forward

    for t in transfers:
        came_in = holder.get(t["payer"])
        if authorizers[t["payer"]] > 0:
            authorizers[t["payer"]] -= 1
            p = {**base, **t, "scheme": "eip3009", "via": None}
        elif BATCH_CONTRACT in (t["payer"], t["payee"]):
            removed.append({**base, **t, "reason": "channel_movement"})
            continue
        elif came_in and SECOND_HOP_SHARE * came_in[1] <= t["atomic"] <= came_in[1]:
            payment = came_in[0]
            payment["via"] = payment["via"] or t["payer"]
            payment["payee"] = t["payee"]
            holder[t["payee"]] = (payment, t["atomic"])
            removed.append({**base, **t, "reason": "second_hop"})
            continue
        elif settles and t["payer"] not in facilitators and not CONTRACTS & {t["payer"], t["payee"]}:
            p = {**base, **t, "scheme": settles.pop(0), "via": None}
        else:
            removed.append({**base, **t, "reason": "non_payment"})
            continue
        payments.append(p)
        holder[t["payee"]] = (p, t["atomic"])

    for l in logs:  # batch claims move no USDC: the payment is the claimed voucher amount
        if _from(l, BATCH_CONTRACT, TOPIC_BATCH_CLAIMED):
            cid = l["topics"][1].lower()
            channel = channels.get(cid, {"payer": f"unknown-payer:{cid[:18]}", "receiver": f"unknown-receiver:{cid[:18]}"})
            payments.append({**base, "log_index": int(l["logIndex"], 16), "payer": channel["payer"],
                             "payee": channel["receiver"], "atomic": int(l["data"][2:66], 16),
                             "scheme": "batch_settlement", "via": None})
    payments.sort(key=lambda p: p["log_index"])
    return {"w0": [{**base, **t} for t in transfers], "payments": payments, "removed": removed}
