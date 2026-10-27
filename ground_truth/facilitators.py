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


def load(cache=Path("out/facilitators.json"), commit=X402SCAN_COMMIT):
    """{address: {"facilitator": id, "deprecated": bool}} for every Base address."""
    if cache.exists():
        data = json.loads(cache.read_text())
        if data["commit"] == commit:
            return data["addresses"]
    names = [f["name"] for f in json.loads(_get(API.format(commit=commit)))
             if f["name"].endswith(".ts") and f["name"] != "index.ts"]
    addresses = {}
    for name in sorted(names):
        for a in parse_base(_get(RAW.format(commit=commit, name=name))):
            addresses[a["address"]] = {"facilitator": name[:-3], "deprecated": a["deprecated"]}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"commit": commit, "addresses": addresses}, indent=1, sort_keys=True))
    return addresses
