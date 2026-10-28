"""Base facilitator addresses from x402scan's registry, pinned at one commit."""
import json
import re
import urllib.request
from pathlib import Path

from .constants import X402SCAN_COMMIT

RAW = "https://raw.githubusercontent.com/Merit-Systems/x402scan/{commit}/packages/external/facilitators/src/facilitators/{name}"
API = "https://api.github.com/repos/Merit-Systems/x402scan/contents/packages/external/facilitators/src/facilitators?ref={commit}"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "x402-ground-truth/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def parse_base(ts_source):
    """Addresses inside the `[Network.BASE]: [ ... ]` block, with their deprecated flag."""
    m = re.search(r"\[Network\.BASE\]:\s*\[(.*?)\n\s*\],", ts_source, re.S)
    if not m:
        return []
    out = []
    for entry in re.findall(r"\{(.*?)\}", m.group(1), re.S):
        addr = re.search(r"address:\s*'(0x[0-9a-fA-F]{40})'", entry)
        if addr:
            out.append({"address": addr.group(1).lower(), "deprecated": "deprecated: true" in entry})
    return out


def parse_facilitator(ts_source):
    """Base addresses with `x402scan_synced`: x402scan's syncer skips deprecated addresses and drops a deprecated
    facilitator entirely (sync/transfers/trigger/lib/facilitators.ts at the pinned commit)."""
    head = ts_source.split("addresses:", 1)[0]
    facilitator_deprecated = re.search(r"deprecated:\s*true", head) is not None
    return [{**a, "x402scan_synced": not (facilitator_deprecated or a["deprecated"])} for a in parse_base(ts_source)]


FORMAT = 2  # bump when the cached shape changes


def load(cache=Path("out/facilitators.json"), commit=X402SCAN_COMMIT):
    """{address: {"facilitator", "deprecated", "x402scan_synced"}} for every Base address."""
    if cache.exists():
        data = json.loads(cache.read_text())
        if data["commit"] == commit and data.get("format") == FORMAT:
            return data["addresses"]
    names = [f["name"] for f in json.loads(_get(API.format(commit=commit)))
             if f["name"].endswith(".ts") and f["name"] != "index.ts"]
    addresses = {}
    for name in sorted(names):
        for a in parse_facilitator(_get(RAW.format(commit=commit, name=name))):
            addresses[a["address"]] = {"facilitator": name[:-3], "deprecated": a["deprecated"],
                                       "x402scan_synced": a["x402scan_synced"]}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"commit": commit, "format": FORMAT, "addresses": addresses}, indent=1, sort_keys=True))
    return addresses
