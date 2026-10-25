#!/usr/bin/env python3
"""Mock 'arbitrary internet host' -- stands in for the pivot target in the
registry-proxy pattern (a config edit that redirects a tool at a destination
nobody approved). Stdlib only. Records every request it ever receives,
including any credential that rode along, so the demo can prove whether
the pivot reached it and what it carried.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

received = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        received.append({"path": self.path, "api_key": self.headers.get("X-Api-Key")})
        print(f"[attacker-target] RECEIVED request #{len(received)}: {self.path} api_key={self.headers.get('X-Api-Key')}")
        if self.path == "/stats":
            self._json(200, {"request_count": len(received), "requests": received})
            return
        self._json(200, {"status": "received", "count": len(received)})

    def _json(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"[attacker-target] {fmt % args}")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8092), Handler).serve_forever()
