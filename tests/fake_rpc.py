"""A local JSON-RPC server for tests: answers from a function, counts requests."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeRpc:
    def __init__(self, answer):
        self.answer, self.requests = answer, []  # answer(method, params) -> result, or raise Rate to send 429
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append(body)
                try:
                    out = [{"jsonrpc": "2.0", "id": c["id"], "result": fake.answer(c["method"], c["params"])} for c in body]
                except Refused:
                    self.send_response(403)
                    self.end_headers()
                    return
                except Rate:
                    self.send_response(429)
                    self.end_headers()
                    return
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


class Rate(Exception):
    pass


class Refused(Exception):  # the node's HTTP 403 on old ranges
    pass
