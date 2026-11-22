"""Governance integration checks using an isolated SQLite database."""
from pathlib import Path

from permission_map.database.db import get_database
from permission_map.importers.csv_importer import import_csv
from permission_map.web.governance import access_inventory, reconcile_hr


def test_hr_reconciliation_flags_leaver_and_unmatched(tmp_path: Path):
    db = get_database(tmp_path / "isolated.db")
    csv_path = tmp_path / "users.csv"
    csv_path.write_text(
        "user_id,name,email,status\n"
        "u1,Former User,former@example.com,active\n"
        "u2,Service,svc@example.com,active\n",
        encoding="utf-8",
    )
    assert import_csv(db, csv_path, entity_type="users").ok
    hr = (
        "employee_id,email,employment_status\n"
        "EMP1,former@example.com,terminated\n"
    )
    result = reconcile_hr(db, hr)
    assert result["totals"]["leaver"] == 1
    assert result["totals"]["unmatched"] == 1
    assert len(access_inventory(db)) == 2


def test_hr_reconciliation_rejects_missing_headers(tmp_path: Path):
    db = get_database(tmp_path / "isolated.db")
    try:
        reconcile_hr(db, "name,email\nSomeone,someone@example.com\n")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected missing HR columns to be rejected")
