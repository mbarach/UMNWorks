"""Tiny local receiver for page data.

The Chrome extension's javascript_tool truncates return values at about 1 KB, so page scripts
POST their JSON here instead (fetch with mode 'no-cors', which lets the request through even
though the page cannot read the response). Each POST is written to OUT_DIR/<name>.json where
<name> comes from the X-Name header or the ?name= query parameter.

Usage: python3 receiver.py OUT_DIR [PORT]
"""
import json, sys, pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

OUT = pathlib.Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
OUT.mkdir(parents=True, exist_ok=True)

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        q = parse_qs(urlparse(self.path).query)
        name = (q.get("name") or [self.headers.get("X-Name") or "dump"])[0]
        name = "".join(ch for ch in name if ch.isalnum() or ch in "-_.") or "dump"
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        path = OUT / f"{name}.json"
        path.write_bytes(body)
        self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers()
        sys.stderr.write(f"wrote {path} ({n} bytes)\n")
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*"); self.end_headers()
    def log_message(self, *a): pass

HTTPServer(("127.0.0.1", PORT), H).serve_forever()
