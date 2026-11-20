"""Tests for the rule-based risk engine."""

from __future__ import annotations

from pathlib import Path

from permission_map.analyzers.risk_engine import RiskEngine
from permission_map.database.db import Database
from permission_map.database.repositories import list_findings
from permission_map.importers.csv_importer import import_csv

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
IMPORT_ORDER = (
    "resources",
    "users",
    "groups",
    "roles",
    "permissions",
    "memberships",
    "role_permissions",
    "role_assignments",
)


def _engine(tmp_path) -> tuple[RiskEngine, Database]:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    for name in IMPORT_ORDER:
        assert import_csv(database, EXAMPLES / f"{name}.csv").ok
    return RiskEngine(database), database


def test_expected_rules_fire(tmp_path) -> None:
    engine, _ = _engine(tmp_path)
    pairs = {(finding.rule, finding.user) for finding in engine.run()}
    assert ("dormant_privileged", "u-1006") in pairs
    assert ("privileged_undeclared", "u-1002") in pairs
    assert ("privileged_undeclared", "u-1007") in pairs
    assert ("privileged_undeclared", "u-1008") in pairs
    assert ("direct_admin", "u-1008") in pairs
    assert ("conflicting_role_types", "u-1002") in pairs
    assert ("excessive_grants", "u-1002") in pairs
    assert ("orphaned_user", "u-1009") in pairs
    assert ("admin_via_broad_group", "u-1002") in pairs


def test_declared_privileged_is_not_undeclared(tmp_path) -> None:
    engine, _ = _engine(tmp_path)
    pairs = {(finding.rule, finding.user) for finding in engine.run()}
    # u-1003 is flagged privileged in the source data, so no mismatch finding.
    assert ("privileged_undeclared", "u-1003") not in pairs


def test_finding_ids_are_stable(tmp_path) -> None:
    engine, _ = _engine(tmp_path)
    first = {finding.finding_id for finding in engine.run()}
    second = {finding.finding_id for finding in engine.run()}
    assert first == second
    assert all(finding_id.startswith("F-") for finding_id in first)


def test_persist_and_fetch(tmp_path) -> None:
    engine, database = _engine(tmp_path)
    findings = engine.run()
    engine.persist(findings)

    rows = list_findings(database)
    assert len(rows) == len(findings)
    assert rows[0]["severity"] == "critical"
    assert any(row["rule"] == "dormant_privileged" for row in rows)


def test_severity_filter(tmp_path) -> None:
    engine, database = _engine(tmp_path)
    engine.persist(engine.run())
    critical = list_findings(database, severity="critical")
    assert critical
    assert all(row["severity"] == "critical" for row in critical)
