"""Keyless JSON-RPC client: batched calls, retry with backoff, on-disk cache."""
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from .constants import RPC_URL


class RpcError(RuntimeError):
    pass


class Rpc:
    def __init__(self, url=RPC_URL, cache_dir=Path("out/cache"), tries=5, pause=1.0):
        self.url, self.tries, self.pause = url, tries, pause
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _post(self, payload):
        body = json.dumps(payload).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json",
                                                      "User-Agent": "x402-ground-truth/0.1"})
        for attempt in range(self.tries):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read())
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = e
                time.sleep(self.pause * 2 ** attempt)
        raise RpcError(f"RPC failed after {self.tries} tries: {last}")

    def batch(self, calls, cache=True):
        """calls: list of (method, params). Returns results in order."""
        key = hashlib.sha256(json.dumps(calls, sort_keys=True).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if cache and path.exists():
            return json.loads(path.read_text())
        payload = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
        for attempt in range(self.tries):
            out = self._post(payload)
            if isinstance(out, dict):  # whole-batch error
                out = [out]
            byid = {o.get("id"): o for o in out}
            errs = [o["error"] for o in out if "error" in o]
            if not errs and len(byid) == len(calls):
                results = [byid[i]["result"] for i in range(len(calls))]
                if cache:
                    path.write_text(json.dumps(results))
                return results
            time.sleep(self.pause * 2 ** attempt)
        raise RpcError(f"batch of {len(calls)} failed after {self.tries} tries: {errs[:1] or 'missing ids'}")

    def call(self, method, params, cache=True):
        return self.batch([(method, params)], cache=cache)[0]
