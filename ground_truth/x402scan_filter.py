"""W0's last step: x402scan's own pass-through collapse, ported from sync/transfers/trigger/lib/collapse.ts at the
pinned commit (its issue #1024).

Inside one transaction, an address that receives USDC and later sends some on is a pass-through. Each chain
payer -> pass-through -> ... -> payee becomes one row: the first leg's payer and log index, the last leg's payee and
amount. In a fan-out the next leg is the one closest in amount; fee legs and legs that don't pair stay as they are.
"""


def collapse(legs):
    """legs: one transaction's USDC transfers ({log_index, payer, payee, atomic, ...}). Rows as x402scan stores them."""
    legs = sorted(legs, key=lambda l: l["log_index"])
    first_in, last_out = {}, {}
    for i, l in enumerate(legs):
        first_in.setdefault(l["payee"], i)
        last_out[l["payer"]] = i
    through = lambda a: a in first_in and a in last_out and first_in[a] < last_out[a]

    used, rows = set(), []
    for i, origin in enumerate(legs):
        if i in used or through(origin["payer"]):
            continue
        used.add(i)
        end = i
        while through(legs[end]["payee"]):
            nexts = [j for j in range(end + 1, len(legs)) if j not in used and legs[j]["payer"] == legs[end]["payee"]]
            if not nexts:
                break
            target = legs[end]["atomic"]
            end = min(nexts, key=lambda j: abs(legs[j]["atomic"] - target))  # ties keep the earliest, as reduce() does
            used.add(end)
        rows.append(origin if end == i else {**origin, "payee": legs[end]["payee"], "atomic": legs[end]["atomic"]})
    rows += [l for j, l in enumerate(legs) if j not in used]
    return rows
