#!/usr/bin/env python3
"""Mock package-registry API: the agent's one legitimate destination.

Stdlib only. Requires `X-Api-Key: registry-secret-9f2` to return real data,
otherwise 401 -- so the demo can tell whether a request arrived with the
real credential attached, not just whether it arrived at all.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

REQUIRED_KEY = "registry-secret-9f2"
request_log = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request_log.append({"path": self.path, "api_key": self.headers.get("X-Api-Key")})
        if self.path == "/stats":
            self._json(200, {"request_count": len(request_log), "requests": request_log})
            return
        if self.headers.get("X-Api-Key") != REQUIRED_KEY:
            self._json(401, {"error": "missing or wrong X-Api-Key"})
            return
        self._json(200, {"package": "agentgateway", "latest": "1.6.0", "registry": "legit-registry"})

    def _json(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"[registry-api] {fmt % args}")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8091), Handler).serve_forever()
