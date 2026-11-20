"""Tests for the identity / permission graph engine."""

from __future__ import annotations

from pathlib import Path

from permission_map.core.graph_engine import PermissionGraph, format_path
from permission_map.database.db import Database
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


def _graph(tmp_path) -> PermissionGraph:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    for name in IMPORT_ORDER:
        result = import_csv(database, EXAMPLES / f"{name}.csv")
        assert result.ok, f"{name}: {result.errors}"
    return PermissionGraph(database)


def test_summary_counts_links(tmp_path) -> None:
    summary = _graph(tmp_path).summary()
    assert summary["users"] == 8
    assert summary["roles"] == 5
    assert summary["permissions"] == 6
    assert summary["role_permissions"] == 8
    assert summary["role_assignments"] == 6


def test_user_roles_via_groups(tmp_path) -> None:
    graph = _graph(tmp_path)
    assert graph.user_roles("u-1002") == ["r-admin", "r-developer", "r-viewer"]


def test_effective_permissions(tmp_path) -> None:
    graph = _graph(tmp_path)
    permissions = {grant.permission_id for grant in graph.describe_user("u-1002").grants}
    assert {"p-aws-admin", "p-github-push", "p-aws-read"} <= permissions


def test_direct_vs_inherited(tmp_path) -> None:
    graph = _graph(tmp_path)
    grants = {grant.permission_id: grant for grant in graph.describe_user("u-1008").grants}
    assert grants["p-aws-admin"].direct is True
    assert grants["p-splunk-read"].direct is False


def test_privileged_users(tmp_path) -> None:
    graph = _graph(tmp_path)
    privileged = set(graph.privileged_users())
    assert {"u-1002", "u-1003", "u-1007", "u-1008"} <= privileged
    assert "u-1004" not in privileged


def test_unknown_user_has_no_access(tmp_path) -> None:
    graph = _graph(tmp_path)
    assert not graph.has_user("nope")
    assert graph.describe_user("nope").grants == []


def test_format_path() -> None:
    assert format_path(["user:u1", "group:g1", "role:r1", "permission:p1"]) == "u1 → g1 → r1 → p1"
