"""Interactive menu shell for PERMISSION MAP.

The default ``permission-map`` startup drops into a small interactive menu that
shows the brand banner and dispatches numbered actions. Items that belong to a
later development phase are answered honestly ("available in Phase N") rather
than pretending to run.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from permission_map import (
    __app_name__,
    __author__,
    __author_linkedin__,
    __linkedin_display__,
    __version__,
)
from permission_map.cli.dashboard import render_app_banner
from permission_map.cli.import_view import render_import_result
from permission_map.cli.list_view import render_list
from permission_map.core.normalizer import normalize_entity
from permission_map.database.db import Database
from permission_map.database.repositories import fetch_records
from permission_map.importers.csv_importer import import_csv
from permission_map.utils.theme import BLUE, CYAN, MUTED_STYLE, WARN_STYLE, WHITE

_NUMBER_STYLE = Style(color=CYAN, bold=True)
_PROMPT_STYLE = Style(color=CYAN, bold=True)

MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("1", "Import Data"),
    ("2", "Analyze Permissions"),
    ("3", "Permission Changes"),
    ("4", "Access Reviews"),
    ("5", "View Findings"),
    ("6", "Generate Reports"),
    ("7", "Settings"),
    ("0", "Exit"),
)

# Which phase delivers each numbered menu item (kept honest while unbuilt).
_PHASE: dict[str, str] = {
    "2": "Phase 4 (analysis engine)",
    "3": "Phase 5 (snapshot comparison)",
    "4": "Phase 7 (review workflow)",
    "5": "Phase 6 (findings & reports)",
    "6": "Phase 6 (HTML/CSV/JSON reports)",
}


def render_menu(console: Console) -> None:
    """Print the numbered action menu."""
    for key, label in MENU_ITEMS:
        line = Text.assemble((" [", MUTED_STYLE), (key, _NUMBER_STYLE), ("] ", MUTED_STYLE))
        line.append(label, style=WHITE)
        line.justify = "center"
        console.print(line)


def render_help(console: Console) -> None:
    """Print the command reference (available from the menu and the CLI)."""
    lines = Group(
        Text("import <file>   import a CSV file of access data", style=WHITE),
        Text("list <entity>   view records (e.g. list users)", style=WHITE),
        Text("dashboard       non-interactive summary", style=WHITE),
        Text("version         print the version", style=WHITE),
        Text("help            show this reference", style=WHITE),
        Text("exit / 0        quit", style=WHITE),
        Text(""),
        Text(
            "Entities: users · groups · roles · resources · permissions · memberships",
            style=MUTED_STYLE,
        ),
        Text(""),
        Text.assemble(
            ("Created by ", MUTED_STYLE),
            (__author__, Style(color=WHITE, bold=True)),
            ("  ·  ", MUTED_STYLE),
            (__linkedin_display__, Style(color=BLUE, link=__author_linkedin__)),
        ),
    )
    panel = Panel(
        lines,
        title=Text("COMMANDS", style=Style(color=CYAN, bold=True)),
        border_style=CYAN,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))


def _ellipsize(value: str, max_length: int = 46) -> str:
    if len(value) <= max_length:
        return value
    keep = (max_length - 1) // 2
    return f"{value[:keep]}…{value[-keep:]}"


def _show_settings(console: Console, db: Database) -> None:
    status = db.status()
    path = Path(status["path"])
    console.print(Text("Settings", style=Style(color=CYAN, bold=True)), justify="center")
    for label, value in (
        ("Data directory", _ellipsize(str(path.parent))),
        ("Database", path.name),
        ("Schema version", f"v{status['schema_version']}"),
        ("Version", __version__),
    ):
        line = Text.assemble((f"{label:<15}", MUTED_STYLE), (value, WHITE))
        line.justify = "center"
        console.print(line)


def handle_command(
    console: Console,
    db: Database,
    choice: str,
    input_fn: Callable[[Text], str] | None = None,
) -> bool:
    """Handle one menu choice. Return False to exit, True to continue."""
    command = choice.strip().lower()
    if command in {"0", "exit", "quit", "q"}:
        return False
    if command == "1":
        read = input_fn or (lambda p: console.input(p))
        raw = read(Text.assemble(("File path: ", WHITE)))
        path = raw.strip()
        if not path:
            console.print(Text("No file given.", style=WARN_STYLE), justify="center")
            return True
        result = import_csv(db, Path(path))
        render_import_result(console, result)
        return True
    if command in {"7", "settings"}:
        _show_settings(console, db)
        return True
    if command == "version":
        console.print(f"{__app_name__} v{__version__}", justify="center")
        return True
    if command in {"help", "?"}:
        render_help(console)
        return True
    if command in {"clear", "cls"}:
        console.clear()
        return True
    if command.startswith("list"):
        entity_name = command.split(" ", 1)[1].strip() if " " in command else ""
        canonical = normalize_entity(entity_name) if entity_name else None
        if canonical is None:
            console.print(
                Text(
                    "Usage: list <users|groups|roles|resources|permissions|memberships>",
                    style=WARN_STYLE,
                ),
                justify="center",
            )
        else:
            render_list(console, canonical, fetch_records(db, canonical))
        return True
    if command in _PHASE:
        label = dict(MENU_ITEMS)[command]
        line = Text.assemble(
            (f"{label} — available in {_PHASE[command]}.", WARN_STYLE)
        )
        line.justify = "center"
        console.print(line)
        return True
    line = Text.assemble(
        ("Unknown option: ", WARN_STYLE),
        (choice, WHITE),
        ("  (type 'help' for options)", MUTED_STYLE),
    )
    line.justify = "center"
    console.print(line)
    return True


def run_shell(
    console: Console,
    db: Database,
    input_fn: Callable[[Text], str] | None = None,
) -> None:
    """Run the interactive menu loop until the user exits."""
    prompt = Text.assemble(("permission-map", _PROMPT_STYLE), (" > ", WHITE))
    read = input_fn or (lambda p: console.input(p))

    render_app_banner(console, db)
    render_menu(console)
    console.print(
        Text("Type 'help' for commands, 'list users' for data, '0' to exit.", style=MUTED_STYLE),
        justify="center",
    )
    console.print("")

    while True:
        try:
            choice = read(prompt)
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not handle_command(console, db, choice, input_fn=read):
            break

    console.print(Text("Goodbye.", style=MUTED_STYLE), justify="center")
