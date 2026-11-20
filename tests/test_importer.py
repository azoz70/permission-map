"""End-to-end tests for the CSV import pipeline."""

from __future__ import annotations

import csv
from pathlib import Path

from permission_map.database.db import Database
from permission_map.importers.csv_importer import import_csv


def _write(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def test_import_users(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    file = tmp_path / "users.csv"
    _write(
        file,
        ["user_id", "name", "email", "is_privileged"],
        [["u1", "Alice", "a@example.com", "false"], ["u2", "Bob", "", "true"]],
    )
    result = import_csv(database, file)
    assert result.ok
    assert result.imported == 2
    assert database.counts()["users"] == 2
    assert database.privileged_user_count() == 1


def test_import_rejects_duplicate_ids(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    file = tmp_path / "users.csv"
    _write(file, ["user_id", "name"], [["u1", "A"], ["u1", "B"]])
    result = import_csv(database, file)
    assert not result.ok
    assert database.counts()["users"] == 0


def test_import_memberships_requires_existing_entities(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    users = tmp_path / "users.csv"
    groups = tmp_path / "groups.csv"
    _write(users, ["user_id"], [["u1"]])
    _write(groups, ["group_id"], [["g1"]])
    assert import_csv(database, users).ok
    assert import_csv(database, groups).ok

    memberships = tmp_path / "memberships.csv"
    _write(memberships, ["user_id", "group_id"], [["u1", "g1"], ["uX", "g1"]])
    result = import_csv(database, memberships)
    assert not result.ok
    assert database.counts()["users"] == 1


def test_import_permissions_requires_resources(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    resources = tmp_path / "resources.csv"
    _write(resources, ["resource_id", "name"], [["res-aws", "AWS"]])
    assert import_csv(database, resources).ok

    permissions = tmp_path / "permissions.csv"
    _write(
        permissions,
        ["permission_id", "resource_id", "action"],
        [["p1", "res-aws", "read"], ["p2", "res-unknown", "read"]],
    )
    result = import_csv(database, permissions)
    assert not result.ok


def test_column_mapping_override(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    file = tmp_path / "people.csv"
    _write(file, ["Username", "Full Name"], [["u1", "Alice"]])
    result = import_csv(
        database,
        file,
        entity_type="users",
        column_overrides={"user_id": "Username", "name": "Full Name"},
    )
    assert result.ok
    assert result.imported == 1
    assert database.counts()["users"] == 1


def test_import_missing_file(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    result = import_csv(database, tmp_path / "nope.csv")
    assert not result.ok
    assert "file not found" in result.errors[0].message
