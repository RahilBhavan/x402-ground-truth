"""Capture x402scan's rolling Base figure from the free tRPC route its web page uses."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://www.x402scan.com/api/trpc/public.stats.overall?input="


def capture(timeframe=7, chain="base", out=Path("out/reconcile/x402scan-capture.json")):
    q = urllib.parse.quote(json.dumps({"json": {"timeframe": timeframe, "chain": chain}}))
    req = urllib.request.Request(URL + q, headers={"User-Agent": "Mozilla/5.0"})
    captured_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
    stats = json.loads(raw)["result"]["data"]["json"]
    record = {"captured_at": captured_at, "timeframe_days": timeframe, "chain": chain,
              "url": URL + q, "raw": raw, "stats": stats,
              "usdc": stats["total_amount"] / 1e6}
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():  # never overwrite a capture: the window is defined by it
        out = out.with_name(f"{out.stem}-{captured_at.replace(':', '')}.json")
    out.write_text(json.dumps(record, indent=1, sort_keys=True))
    return out, record
