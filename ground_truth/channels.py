"""Batch-settlement channels: channelId -> payer and receiver, from ChannelCreated logs.

The keyless node allows eth_getLogs over at most 50,000 blocks and refuses old state, so the lookup walks back
from the window in 50,000-block spans, stopping when every id is found or at FLOOR blocks back. Unfound ids stay
unknown and are reported."""
from .constants import BATCH_CONTRACT, TOPIC_BATCH_CHANNEL_CREATED
from .rpc import RpcError
SPAN = 50_000
FLOOR = 2_000_000  # about 46 days of Base blocks; the node refused ranges about 2.1M blocks behind its head


def word(data, i):
    return data[2 + 64 * i: 2 + 64 * (i + 1)]


def lookup(rpc, channel_ids, last_block):
    """{channelId: {"payer", "receiver"}} for each id found within FLOOR blocks before last_block."""
    wanted, found = set(channel_ids), {}
    b = last_block
    while wanted - set(found) and b > last_block - FLOOR:
        a = max(b - SPAN + 1, last_block - FLOOR + 1)
        try:
            logs = rpc.call("eth_getLogs", [{"address": BATCH_CONTRACT, "fromBlock": hex(a), "toBlock": hex(b),
                                             "topics": [TOPIC_BATCH_CHANNEL_CREATED, sorted(wanted - set(found))]}],
                            label=f"ChannelCreated {a}-{b}")
        except RpcError:  # the node refuses ranges far behind its head (HTTP 403): history ends here
            break
        for l in logs:  # data: ChannelConfig(payer, payerAuthorizer, receiver, receiverAuthorizer, token, delay, salt)
            found[l["topics"][1].lower()] = {"payer": "0x" + word(l["data"], 0)[-40:],
                                             "receiver": "0x" + word(l["data"], 2)[-40:]}
        b = a - 1
    return found
