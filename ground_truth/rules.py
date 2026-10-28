"""Rules W1-W5 (docs/prd/2-evidence.md, thresholds in docs/preregistration.md). Each rule after W1 is a pure function
from the payments that survived the rules before it to the payments it removes. A payment is a dict with tx,
log_index, block, payer, payee and atomic.

W1 is the per-transaction classifier in settlements.py, named here so every rule has one home.
"""
from collections import Counter, defaultdict

from .settlements import classify as w1  # noqa: F401  (W1: attribution, one facilitator transaction at a time)

BASE_GENESIS_TS = 1686789347  # Base block n has timestamp 1686789347 + 2n (checked against the node, source O8)
DAY_BLOCKS = 43_200  # 24 hours of 2-second blocks
DEFAULTS = {"w3_share": 0.9, "w4_payments": 3, "w4_payers": 2, "w5_burst": 1000}


def key(p):
    return p["tx"], p["log_index"]


def utc_day(block):
    return (BASE_GENESIS_TS + 2 * block) // 86_400


def w2(payments):
    """Payer and payee are the same address."""
    return [p for p in payments if p["payer"] == p["payee"]]


def w3(payments, returns, share=DEFAULTS["w3_share"], window=DAY_BLOCKS):
    """The payee sends at least `share` of the payment back to the payer, after it and within `window` blocks, in any
    transaction. `returns` are USDC transfers (payer = sender). Each return cancels one payment, earliest first."""
    back = defaultdict(list)
    for r in sorted(returns, key=lambda r: (r["block"], r["log_index"])):
        back[(r["payer"], r["payee"])].append(r)
    used, removed = set(), []
    for p in sorted(payments, key=lambda p: (p["block"], p["log_index"], p["tx"])):
        for r in back.get((p["payee"], p["payer"]), ()):
            if (r["block"], r["log_index"]) <= (p["block"], p["log_index"]) or key(r) in used:
                continue
            if r["block"] > p["block"] + window:
                break
            if r["atomic"] >= share * p["atomic"]:
                used.add(key(r))
                removed.append(p)
                break
    return removed


def w4(payments, min_payments=DEFAULTS["w4_payments"], min_payers=DEFAULTS["w4_payers"]):
    """The payee has fewer than `min_payments` payments, or fewer than `min_payers` distinct payers, in the window."""
    count, payers = Counter(p["payee"] for p in payments), defaultdict(set)
    for p in payments:
        payers[p["payee"]].add(p["payer"])
    thin = {e for e in count if count[e] < min_payments or len(payers[e]) < min_payers}
    return [p for p in payments if p["payee"] in thin]


def w5(payments, burst=DEFAULTS["w5_burst"]):
    """The payer-payee pair made at least `burst` payments of one identical amount on one UTC day."""
    group = lambda p: (p["payer"], p["payee"], utc_day(p["block"]), p["atomic"])
    size = Counter(group(p) for p in payments)
    return [p for p in payments if size[group(p)] >= burst]


ORDER = (  # (rule, label, removed payments given the survivors, the returns and the thresholds)
    ("W2", "self-payment", lambda ps, rs, t: w2(ps)),
    ("W3", "round trip", lambda ps, rs, t: w3(ps, rs, t["w3_share"])),
    ("W4", "thin seller", lambda ps, rs, t: w4(ps, t["w4_payments"], t["w4_payers"])),
    ("W5", "farming burst", lambda ps, rs, t: w5(ps, t["w5_burst"])),
)


def apply(payments, returns, **thresholds):
    """[(rule, label, removed payments)] in order, and the payments kept."""
    t = {**DEFAULTS, **thresholds}
    steps, kept = [], list(payments)
    for rule, label, remove in ORDER:
        out = remove(kept, returns, t)
        gone = {key(p) for p in out}
        kept = [p for p in kept if key(p) not in gone]
        steps.append((rule, label, out))
    return steps, kept
