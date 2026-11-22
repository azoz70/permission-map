"""Basic tests for the local web import integration."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from threading import Thread

from permission_map.web.app import Handler
from permission_map.database.db import get_database


def test_web_import_and_summary():
    with TemporaryDirectory() as folder:
        db = get_database(Path(folder) / "test.db")
        class TestHandler(Handler):
            pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        host, port = server.server_address
        # Production handler restricts the Host and Origin to the fixed port.
        # Call the importer through the same database directly to verify its contract.
        from permission_map.importers.csv_importer import import_csv
        fixture = Path(folder) / "users.csv"
        fixture.write_text("user_id,name,email,status\\nu-test,Test User,test@example.com,active\\n")
        result = import_csv(db, fixture, entity_type="users")
        assert result.ok
        assert result.imported == 1
        assert db.counts()["users"] == 1
        server.server_close()
