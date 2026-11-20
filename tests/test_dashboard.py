"""Tests for the dashboard renderer (captured, non-terminal output)."""

from __future__ import annotations

import io

from rich.console import Console

from permission_map.cli.dashboard import (
    render_dashboard,
    render_overview,
    render_status_lines,
)
from permission_map.cli.logo import render_logo
from permission_map.database.db import Database


def _console() -> Console:
    return Console(file=io.StringIO(), width=110, force_terminal=False)


def test_logo_renders_name_and_tagline() -> None:
    console = _console()
    render_logo(console)
    output = console.file.getvalue()  # type: ignore[union-attr]
    assert "P E R M I S S I O N   M A P" in output
    assert "ACCESS INTELLIGENCE ENGINE" in output
    assert "IDENTITY" in output
    assert "ACCESS" in output
    assert "VISIBILITY" in output


def test_status_lines_show_real_state(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    render_status_lines(console, database)
    output = console.file.getvalue()  # type: ignore[union-attr]
    assert "SYSTEM" in output and "INITIALIZED" in output
    assert "DATABASE" in output and "READY" in output
    assert "ENGINE" in output and "STANDBY" in output


def test_overview_shows_real_zero_counts(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    render_overview(console, database)
    output = console.file.getvalue()  # type: ignore[union-attr]
    for label in ("USERS", "GROUPS", "ROLES", "RESOURCES", "PRIVILEGED", "FINDINGS"):
        assert label in output


def test_dashboard_renders_all_sections(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    render_dashboard(console, database)
    output = console.file.getvalue()  # type: ignore[union-attr]
    assert "P E R M I S S I O N   M A P" in output
    assert "QUICK OVERVIEW" in output
    assert "COMMANDS" in output


def test_dashboard_shows_author_attribution(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    render_dashboard(console, database)
    output = console.file.getvalue()  # type: ignore[union-attr]
    assert "Created by" in output
    assert "Abdulaziz Alshehri" in output
    assert "linkedin.com" in output
