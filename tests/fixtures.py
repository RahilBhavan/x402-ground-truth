"""Hand-built receipts. Addresses are short hex ids padded to 20 bytes."""
from ground_truth.constants import (PROXIES, TOPIC_AUTHORIZATION_USED, TOPIC_BATCH_CLAIMED, TOPIC_PROXY_SETTLED,
                                    TOPIC_TRANSFER, USDC)

FAC = "0x" + "fa" * 20
PAYER, PAYEE, ROUTER, OTHER = ("0x" + c * 40 for c in "1234")
FACILITATORS = {FAC: {"facilitator": "test", "deprecated": False}}


def topic(addr):
    return "0x" + "0" * 24 + addr[2:]


def transfer(i, frm, to, amount):
    return {"address": USDC, "logIndex": hex(i), "topics": [TOPIC_TRANSFER, topic(frm), topic(to)],
            "data": hex(amount)}


def auth_used(i, authorizer):
    return {"address": USDC, "logIndex": hex(i), "topics": [TOPIC_AUTHORIZATION_USED, topic(authorizer), "0x" + "ab" * 32],
            "data": "0x"}


def proxy_settled(i, scheme="upto"):
    return {"address": PROXIES[scheme], "logIndex": hex(i), "topics": [TOPIC_PROXY_SETTLED], "data": "0x"}


def claimed(i, channel, amount):
    data = "0x" + format(amount, "064x") + format(amount, "064x")
    return {"address": PROXIES["batch_settlement"], "logIndex": hex(i),
            "topics": [TOPIC_BATCH_CLAIMED, "0x" + channel * 32, topic(FAC)], "data": data}


def receipt(logs, h="0x" + "aa" * 32):
    return {"transactionHash": h, "status": "0x1", "logs": logs}
