"""Smoke test: the web interface uses the existing validated CSV importer."""
from pathlib import Path

from permission_map.database.db import get_database
from permission_map.importers.csv_importer import import_csv


def test_csv_import_contract(tmp_path: Path):
    db = get_database(tmp_path / "test.db")
    fixture = tmp_path / "users.csv"
    fixture.write_text("user_id,name,email,status\nu-test,Test User,test@example.com,active\n")
    result = import_csv(db, fixture, entity_type="users")
    assert result.ok
    assert result.imported == 1
    assert db.counts()["users"] == 1
