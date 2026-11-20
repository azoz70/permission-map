"""Tests for the interactive menu command dispatcher."""

from __future__ import annotations

import csv
import io

from rich.console import Console
from rich.text import Text

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


def test_import_menu_runs_import(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    file = tmp_path / "users.csv"
    with file.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "name"])
        writer.writerow(["u1", "Alice"])

    console = _console()

    def input_fn(prompt: Text) -> str:
        return str(file)

    assert handle_command(console, database, "1", input_fn=input_fn) is True
    assert "IMPORT RESULT" in console.file.getvalue()  # type: ignore[union-attr]
    assert database.counts()["users"] == 1


def test_settings_shows_real_values(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "7") is True
    assert "Schema version" in console.file.getvalue()  # type: ignore[union-attr]


def test_unbuilt_item_reports_phase(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "3") is True
    assert "Phase 5" in console.file.getvalue()  # type: ignore[union-attr]


def test_unknown_option_is_handled(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "nope") is True
    assert "Unknown option" in console.file.getvalue()  # type: ignore[union-attr]


def test_import_command_with_path(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    file = tmp_path / "users.csv"
    with file.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "name"])
        writer.writerow(["u1", "Alice"])

    console = _console()
    assert handle_command(console, database, f"import {file}") is True
    assert "IMPORT RESULT" in console.file.getvalue()  # type: ignore[union-attr]
    assert database.counts()["users"] == 1


def test_dashboard_command_in_menu(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "dashboard") is True
    assert "QUICK OVERVIEW" in console.file.getvalue()  # type: ignore[union-attr]


def test_help_is_clear(tmp_path) -> None:
    database = Database(tmp_path / "pm.db")
    database.initialize()
    console = _console()
    assert handle_command(console, database, "help") is True
    output = console.file.getvalue()  # type: ignore[union-attr]
    assert "IMPORT DATA" in output
    assert "VIEW DATA" in output
    assert "list memberships" in output
