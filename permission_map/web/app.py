"""Loopback-only local web UI for PERMISSION MAP.

CSV imports use the existing validated importer. No cloud services are contacted.
"""
from __future__ import annotations

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from urllib.parse import urlparse

from permission_map.core.graph_engine import PermissionGraph
from permission_map.core.normalizer import FIELDS
from permission_map.database.db import get_database
from permission_map.importers.csv_importer import import_csv

STATIC = Path(__file__).with_name("index.html")
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
LOCAL_HOSTS = {"127.0.0.1:8765", "localhost:8765"}


def summary() -> dict:
    db = get_database()
    return {**PermissionGraph(db).summary(), "resources": db.counts()["resources"]}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, payload: bytes, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type + ("; charset=utf-8"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def reply_json(self, status, value):
        self.respond(status, json.dumps(value).encode())

    def do_GET(self):
        if self.headers.get("Host") not in LOCAL_HOSTS:
            return self.reply_json(403, {"error": "Invalid host"})
        path = urlparse(self.path).path
        if path == "/":
            return self.respond(200, STATIC.read_bytes(), "text/html")
        if path == "/api/summary":
            try:
                return self.reply_json(200, summary())
            except Exception:
                return self.reply_json(500, {"error": "Unable to load local database"})
        return self.reply_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.headers.get("Host") not in LOCAL_HOSTS:
            return self.reply_json(403, {"error": "Invalid host"})
        origin = self.headers.get("Origin", "")
        if origin not in {"http://127.0.0.1:8765", "http://localhost:8765"}:
            return self.reply_json(403, {"error": "Same-origin request required"})
        if urlparse(self.path).path != "/api/import":
            return self.reply_json(404, {"error": "Not found"})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.reply_json(415, {"error": "Expected JSON"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.reply_json(400, {"error": "Invalid request size"})
        if not 0 < size <= MAX_UPLOAD_BYTES:
            return self.reply_json(413, {"error": "Request must be under 2 MB"})
        try:
            body = json.loads(self.rfile.read(size))
            entity = body.get("entity")
            content = body.get("content")
            if entity not in FIELDS or not isinstance(content, str):
                return self.reply_json(400, {"error": "Invalid entity or CSV content"})
            if len(content.encode("utf-8")) > MAX_UPLOAD_BYTES:
                return self.reply_json(413, {"error": "CSV too large"})
            # A temporary local CSV is required by the existing import pipeline.
            with tempfile.TemporaryDirectory(prefix="permission-map-") as folder:
                path = Path(folder) / (entity + ".csv")
                path.write_text(content, encoding="utf-8")
                result = import_csv(get_database(), path, entity_type=entity)
            return self.reply_json(200 if result.ok else 422, {
                "ok": result.ok, "entity": result.entity,
                "total_rows": result.total_rows, "imported": result.imported,
                "mapped": result.mapped,
                "issues": [asdict(issue) for issue in result.issues],
            })
        except (ValueError, UnicodeError, TypeError):
            return self.reply_json(400, {"error": "Malformed upload"})
        except Exception:
            return self.reply_json(500, {"error": "Import failed; check local logs"})

    def log_message(self, format, *args):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("PERMISSION MAP local web: http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
