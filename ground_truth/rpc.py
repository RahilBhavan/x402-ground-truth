"""Keyless JSON-RPC client: batched calls, retry with backoff, on-disk cache per request.

GROUND_TRUTH_RPC overrides the endpoint and GROUND_TRUTH_RPC_PAUSE the first backoff (tests use a fake server).
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .constants import RPC_URL


class RpcError(RuntimeError):
    pass


class Rpc:
    def __init__(self, url=None, cache_dir=Path("out/cache"), tries=5, pause=None):
        self.url = url or os.environ.get("GROUND_TRUTH_RPC", RPC_URL)
        self.tries = tries
        self.pause = float(os.environ.get("GROUND_TRUTH_RPC_PAUSE", 1.0)) if pause is None else pause
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _post(self, payload):
        req = urllib.request.Request(self.url, json.dumps(payload).encode(),
                                     {"Content-Type": "application/json", "User-Agent": "x402-ground-truth/0.1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())

    def batch(self, calls, cache=True, label="", shrink=None):
        """calls: list of (method, params). Results in order. A cached request is never sent again.
        shrink(result) keeps only the fields a caller needs, before caching, so a 7-day cache stays small."""
        key = hashlib.sha256(json.dumps(calls, sort_keys=True).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if cache and path.exists():
            return json.loads(path.read_text())
        payload = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
        last = "no response"
        for attempt in range(self.tries):
            try:
                out = self._post(payload)
                out = [out] if isinstance(out, dict) else out
                byid = {o.get("id"): o for o in out}
                errors = [o["error"] for o in out if "error" in o]
                if not errors and len(byid) == len(calls):
                    results = [byid[i]["result"] for i in range(len(calls))]
                    if shrink:
                        results = [shrink(r) for r in results]
                    if cache:
                        path.write_text(json.dumps(results))
                    return results
                last = errors[0] if errors else "missing ids in batch response"
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as e:
                last = e
            if attempt < self.tries - 1:
                time.sleep(self.pause * 2 ** attempt)
        raise RpcError(f"RPC failed{' for ' + label if label else ''} after {self.tries} tries: {last}")

    def call(self, method, params, cache=True, label=""):
        return self.batch([(method, params)], cache=cache, label=label)[0]
