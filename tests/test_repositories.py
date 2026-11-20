"""Tests for the repository query helpers."""

from __future__ import annotations

import csv

from permission_map.database.db import Database
from permission_map.database.repositories import fetch_records
from permission_map.importers.csv_importer import import_csv


def _write_users(path, rows) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "name", "is_privileged"])
        writer.writerows(rows)


def test_fetch_records_returns_imported_users(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    file = tmp_path / "users.csv"
    _write_users(file, [["u1", "Alice", "false"], ["u2", "Bob", "true"]])
    assert import_csv(database, file).ok

    records = fetch_records(database, "users")
    assert len(records) == 2
    assert records[0]["external_id"] == "u1"
    assert records[1]["is_privileged"] == 1  # SQLite stores booleans as 0/1


def test_fetch_records_empty_database(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    assert fetch_records(database, "users") == []
