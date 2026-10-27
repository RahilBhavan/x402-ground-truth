"""AC-5: what the log path misses. Scan every block in a range for transactions a facilitator sent, and bound the
count with each facilitator's nonce at the range edges."""
import json
from pathlib import Path

BLOCKS_PER_BATCH = 10


def scan(rpc, first, last, facilitators, cache=Path("out/scan")):
    """Sorted hashes of every transaction sent by a listed facilitator in [first, last]. Compact cache per batch."""
    cache.mkdir(parents=True, exist_ok=True)
    found = []
    for a in range(first, last + 1, BLOCKS_PER_BATCH):
        b = min(a + BLOCKS_PER_BATCH - 1, last)
        path = cache / f"{a}-{b}.json"
        if path.exists():
            found += json.loads(path.read_text())
            continue
        blocks = rpc.batch([("eth_getBlockByNumber", [hex(n), True]) for n in range(a, b + 1)], cache=False,
                           label=f"blocks {a}-{b}")
        hits = sorted(t["hash"] for blk in blocks for t in blk["transactions"] if t["from"].lower() in facilitators)
        path.write_text(json.dumps(hits))
        found += hits
    return sorted(found)


def nonce_count(rpc, first, last, facilitators):
    """Transactions sent by all listed facilitators in [first, last], from nonces before and at the range."""
    addrs = sorted(facilitators)
    before = rpc.batch([("eth_getTransactionCount", [a, hex(first - 1)]) for a in addrs], label=f"nonces at {first - 1}")
    after = rpc.batch([("eth_getTransactionCount", [a, hex(last)]) for a in addrs], label=f"nonces at {last}")
    return sum(int(y, 16) - int(x, 16) for x, y in zip(before, after))
