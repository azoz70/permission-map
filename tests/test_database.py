"""Tests for the SQLite database layer."""

from __future__ import annotations

from permission_map.database.db import SCHEMA_VERSION, Database

EXPECTED_ENTITY_TABLES = {"users", "groups", "roles", "resources", "permissions"}


def test_initialize_creates_schema(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    assert not database.exists()
    database.initialize()
    assert database.exists()
    assert database.schema_version() == SCHEMA_VERSION


def test_counts_start_at_zero(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    counts = database.counts()
    assert set(counts) == EXPECTED_ENTITY_TABLES
    assert all(value == 0 for value in counts.values())


def test_status_reports_real_state(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    status = database.status()
    assert status["initialized"] is True
    assert status["schema_version"] == SCHEMA_VERSION
    assert status["last_analysis_at"] is None
    assert status["counts"]["users"] == 0


def test_uninitialized_status_is_honest(tmp_path) -> None:
    database = Database(tmp_path / "does-not-exist.db")
    status = database.status()
    assert status["initialized"] is False
    assert status["schema_version"] is None


def test_initialize_is_idempotent(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    database.initialize()
    database.initialize()
    assert database.schema_version() == SCHEMA_VERSION
