"""Local-only HTTP interface for access governance.

Start: python -m permission_map.web.app
"""
from __future__ import annotations

import csv
import html
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from permission_map.database.db import Database
from permission_map.core.graph_engine import PermissionGraph

DATA_DIR = Path.home() / ".permission-map"
STATIC = Path(__file__).with_name("index.html")


def summary() -> dict:
    db = Database(DATA_DIR / "permission_map.db")
    db.initialize()
    graph = PermissionGraph(db)
    return graph.summary()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            payload = STATIC.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif path == "/api/summary":
            try:
                payload = json.dumps(summary()).encode()
                self.send_response(200)
            except Exception:
                payload = b'{"error":"Unable to load local summary"}'
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
        else:
            self.send_error(404)
            return
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self.send_error(405, "Import and review writes are not enabled yet")

    def log_message(self, format, *args):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("PERMISSION MAP: http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
