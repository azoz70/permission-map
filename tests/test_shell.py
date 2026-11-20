"""Tests for the interactive menu command dispatcher."""

from __future__ import annotations

import io

from rich.console import Console

from permission_map.cli.shell import MENU_ITEMS, handle_command
from permission_map.database.db import Database


def _console() -> Console:
    return Console(file=io.StringIO(), width=110, force_terminal=False)


def test_menu_has_expected_items() -> None:
    labels = dict(MENU_ITEMS)
    assert labels["0"] == "Exit"
    assert labels["1"] == "Import Data"
    assert labels["7"] == "Settings"


def test_exit_returns_false(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    assert handle_command(_console(), database, "0") is False
    assert handle_command(_console(), database, "exit") is False


def test_import_reports_phase_2(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "1") is True
    assert "Phase 2" in console.file.getvalue()  # type: ignore[union-attr]


def test_settings_shows_real_values(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "7") is True
    output = console.file.getvalue()  # type: ignore[union-attr]
    assert "Schema version" in output


def test_unknown_option_is_handled(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "nope") is True
    assert "Unknown option" in console.file.getvalue()  # type: ignore[union-attr]
