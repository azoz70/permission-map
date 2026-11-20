"""Tests for the dashboard renderer (captured, non-terminal output)."""

from __future__ import annotations

import io

from rich.console import Console

from permission_map.cli.dashboard import render_dashboard
from permission_map.database.db import Database


def _render(tmp_path, logo_index: int = 1) -> str:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = Console(file=io.StringIO(), width=110, force_terminal=False)
    render_dashboard(console, database, logo_index=logo_index)
    return console.file.getvalue()  # type: ignore[union-attr]


def test_dashboard_shows_brand_and_version(tmp_path) -> None:
    output = _render(tmp_path)
    assert "PERMISSION MAP" in output
    assert "ACCESS INTELLIGENCE" in output
    assert "v0.1.0" in output


def test_dashboard_shows_real_zero_counts(tmp_path) -> None:
    output = _render(tmp_path)
    for label in (
        "Total Users",
        "Total Groups",
        "Total Roles",
        "Total Resources",
        "Total Permissions",
    ):
        assert label in output
    # An empty database must be reported as zeros, never as sample numbers.
    assert "Total Users" in output


def test_dashboard_shows_database_status(tmp_path) -> None:
    output = _render(tmp_path)
    assert "DATABASE" in output
    assert "Last analysis" in output
    assert "never" in output


def test_dashboard_renders_every_logo_variant(tmp_path) -> None:
    for index in range(5):
        output = _render(tmp_path, logo_index=index)
        assert "PERMISSION MAP" in output
