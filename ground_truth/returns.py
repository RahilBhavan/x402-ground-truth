"""W3's second log query: USDC transfers from a payee back to one of its payers, from the window's first block to
24 hours after its last (`rules.DAY_BLOCKS`). Payees are queried in groups, with their payers as the second topic
list; the node returns every transfer from any payee in the group to any payer in it, and only real pairs are kept.

The end block is fixed, so the query is the same on every run; it refuses to start before the chain reaches it.
"""
from concurrent.futures import ThreadPoolExecutor

from .constants import TOPIC_TRANSFER, USDC
from .rpc import RpcError
from .rules import DAY_BLOCKS

SPAN = 50_000  # the node's eth_getLogs block limit
GROUP = 200  # payees per query
MAX_PAYERS = 3_000  # payers per query (tested: 200 x 3,000 topics answer in about 25 s)


class NotReady(RuntimeError):
    pass


def pad(address):
    return "0x" + "0" * 24 + address[2:]


def groups(pairs):
    """Payee groups of at most GROUP payees and MAX_PAYERS payers, from {(payer, payee)}."""
    payers = {}
    for payer, payee in pairs:
        payers.setdefault(payee, set()).add(payer)
    out, cur, cur_payers = [], [], set()
    for e in sorted(payers):
        mine = sorted(payers[e])
        if len(mine) > MAX_PAYERS:  # one payee with more payers than a query holds gets queries of its own
            out += [([e], mine[i:i + MAX_PAYERS]) for i in range(0, len(mine), MAX_PAYERS)]
            continue
        if cur and (len(cur) >= GROUP or len(cur_payers | payers[e]) > MAX_PAYERS):
            out.append((cur, sorted(cur_payers)))
            cur, cur_payers = [], set()
        cur.append(e)
        cur_payers |= payers[e]
    if cur:
        out.append((cur, sorted(cur_payers)))
    return out


def logs(rpc, payees, payers, a, b):
    try:
        return rpc.call("eth_getLogs", [{"address": USDC, "fromBlock": hex(a), "toBlock": hex(b),
                                         "topics": [TOPIC_TRANSFER, [pad(x) for x in payees], [pad(x) for x in payers]]}],
                        label=f"returns {payees[0][:10]}+{len(payees) - 1} {a}-{b}")
    except RpcError:
        if b - a < 1_000:
            raise
        mid = (a + b) // 2  # a span holding more than the node's result cap: split it
        return logs(rpc, payees, payers, a, mid) + logs(rpc, payees, payers, mid + 1, b)


def fetch(rpc, pairs, first, last, workers=4):
    """Return transfers {tx, log_index, block, payer (sender), payee (recipient), atomic} for (payer, payee) pairs."""
    if not pairs:
        return []
    end = last + DAY_BLOCKS
    head = int(rpc.call("eth_blockNumber", [], cache=False, label="head"), 16)
    if head < end:
        raise NotReady(f"W3 needs block {end:,}; the head is {head:,}, about {(end - head) * 2 / 3600:.1f} hours away")
    jobs = [(g, a, min(a + SPAN - 1, end)) for g in groups(pairs) for a in range(first, end + 1, SPAN)]
    with ThreadPoolExecutor(workers) as pool:
        parts = pool.map(lambda j: logs(rpc, *j[0], j[1], j[2]), jobs)
    wanted = {(payee, payer) for payer, payee in pairs}  # a return goes from the payment's payee to its payer
    out = {}
    for l in (l for part in parts for l in part):
        frm, to = "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:]
        if (frm, to) in wanted:
            out[(l["transactionHash"], int(l["logIndex"], 16))] = {
                "tx": l["transactionHash"], "log_index": int(l["logIndex"], 16), "block": int(l["blockNumber"], 16),
                "payer": frm, "payee": to, "atomic": int(l["data"], 16)}
    return [out[k] for k in sorted(out)]
