"""Loopback-only local web UI for PERMISSION MAP."""

from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import json
import logging
import re
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from permission_map.core.graph_engine import PermissionGraph
from permission_map.core.normalizer import FIELDS
from permission_map.database.db import get_database
from permission_map.importers.csv_importer import import_rows, read_tabular_rows
from permission_map.importers.excel import read_excel
from permission_map.reporters.campaign_csv import campaign_csv
from permission_map.web import campaigns
from permission_map.web.governance import access_inventory, reconcile_hr

STATIC = Path(__file__).with_name("index.html").read_bytes()
SCRIPT_HASH = base64.b64encode(
    hashlib.sha256(STATIC.split(b"<script>", 1)[1].split(b"</script>", 1)[0]).digest()
).decode("ascii")
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
LOCAL_HOSTS = {"127.0.0.1:8765", "localhost:8765"}
CAMPAIGN_PATH = re.compile(r"/api/campaigns/([1-9][0-9]{0,17})(.*)")
ITEM_PATH = re.compile(r"/items/([1-9][0-9]{0,17})")


def summary() -> dict:
    db = get_database()
    return {**PermissionGraph(db).summary(), "resources": db.counts()["resources"]}


def import_upload(body):
    entity, content = body.get("entity"), body.get("content")
    if not isinstance(entity, str) or entity not in FIELDS or not isinstance(content, str):
        raise ValueError("Invalid entity or content")
    file_format = body.get("format", "csv")
    if file_format == "xlsx":
        headers, rows = read_excel(base64.b64decode(content, validate=True))
    elif file_format == "csv":
        headers, rows = read_tabular_rows(
            csv.reader(StringIO(content.lstrip("\ufeff")), strict=True)
        )
    else:
        raise ValueError("Choose CSV or XLSX")
    result = import_rows(get_database(), Path(f"{entity}.{file_format}"), headers, rows, entity)
    return (200 if result.ok else 422), {
        "ok": result.ok,
        "entity": result.entity,
        "total_rows": result.total_rows,
        "imported": result.imported,
        "mapped": result.mapped,
        "issues": [asdict(issue) for issue in result.issues],
    }


class Handler(BaseHTTPRequestHandler):
    timeout = 15

    def respond(self, status: int, payload: bytes, content_type="application/json", filename=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            f"default-src 'self'; script-src 'sha256-{SCRIPT_HASH}'; "
            "style-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def reply_json(self, status, value):
        self.respond(status, json.dumps(value).encode())

    def _dispatch(self, operation):
        if self.headers.get_all("Host") not in [[host] for host in LOCAL_HOSTS]:
            return self.reply_json(403, {"error": "Invalid host"})
        try:
            return operation()
        except LookupError as exc:
            return self.reply_json(404, {"error": str(exc)})
        except campaigns.CampaignConflict as exc:
            return self.reply_json(409, {"error": str(exc)})
        except (ValueError, csv.Error, binascii.Error) as exc:
            return self.reply_json(422, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return None
        except Exception:
            logging.exception("Local request failed")
            return self.reply_json(500, {"error": "Local request failed"})

    def do_GET(self):
        return self._dispatch(self._get)

    def _get(self):
        url = urlparse(self.path)
        if url.path == "/":
            return self.respond(200, STATIC, "text/html")
        if url.path == "/api/access":
            return self.reply_json(200, {"users": access_inventory(get_database())})
        if url.path == "/api/summary":
            return self.reply_json(200, summary())
        if url.path == "/api/campaigns":
            return self.reply_json(200, {"campaigns": campaigns.list_campaigns(get_database())})
        match = CAMPAIGN_PATH.fullmatch(url.path)
        if match:
            campaign_id, suffix = int(match[1]), match[2]
            db = get_database()
            if suffix == "":
                after = int(parse_qs(url.query).get("after", ["0"])[0])
                if not 0 <= after <= 2**63 - 1:
                    raise ValueError("Invalid page cursor")
                return self.reply_json(200, campaigns.campaign_report(db, campaign_id, 25, after))
            if suffix == "/report.json":
                report = campaigns.campaign_report(db, campaign_id, include_audit=True)
                return self.respond(
                    200, json.dumps(report).encode(), filename=f"campaign-{campaign_id}.json"
                )
            if suffix == "/report.csv":
                report = campaigns.campaign_report(db, campaign_id)
                return self.respond(
                    200, campaign_csv(report), "text/csv", f"campaign-{campaign_id}.csv"
                )
        return self.reply_json(404, {"error": "Not found"})

    def do_POST(self):
        return self._dispatch(self._post)

    def _post(self):
        if self.headers.get_all("Origin") != ["http://" + self.headers["Host"]]:
            return self.reply_json(403, {"error": "Same-origin request required"})
        if self.headers.get_content_type() != "application/json":
            return self.reply_json(415, {"error": "Expected JSON"})
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
            return self.reply_json(400, {"error": "Expected one Content-Length"})
        try:
            size = int(lengths[0])
        except ValueError:
            return self.reply_json(400, {"error": "Invalid request size"})
        if not 0 < size <= MAX_UPLOAD_BYTES:
            return self.reply_json(413, {"error": "Request must be at most 8 MiB"})
        try:
            body = json.loads(self.rfile.read(size))
        except (ValueError, RecursionError):
            return self.reply_json(400, {"error": "Malformed JSON"})
        if not isinstance(body, dict):
            return self.reply_json(400, {"error": "Expected a JSON object"})
        path = urlparse(self.path).path
        if path == "/api/import":
            return self.reply_json(*import_upload(body))
        if path == "/api/hr-reconcile":
            if not isinstance(body.get("content"), str):
                return self.reply_json(400, {"error": "Invalid HR content"})
            return self.reply_json(200, reconcile_hr(get_database(), body["content"]))
        if path == "/api/campaigns":
            campaign_id = campaigns.create_campaign(get_database(), body)
            return self.reply_json(201, {"id": campaign_id})
        match = CAMPAIGN_PATH.fullmatch(path)
        if match:
            campaign_id, suffix = int(match[1]), match[2]
            if suffix == "/close":
                campaigns.close_campaign(get_database(), campaign_id)
                return self.reply_json(200, {"ok": True})
            item = ITEM_PATH.fullmatch(suffix)
            if item:
                campaigns.decide(get_database(), campaign_id, int(item[1]), body)
                return self.reply_json(200, {"ok": True})
        return self.reply_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        pass


def main():
    with ThreadingHTTPServer(("127.0.0.1", 8765), Handler) as server:
        print("PERMISSION MAP local web: http://127.0.0.1:8765", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
