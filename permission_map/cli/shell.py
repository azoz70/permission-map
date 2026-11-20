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
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map import (
    __app_name__,
    __author__,
    __author_linkedin__,
    __linkedin_display__,
    __version__,
)
from permission_map.cli.dashboard import render_app_banner, render_dashboard
from permission_map.cli.import_view import render_import_result
from permission_map.cli.list_view import render_list
from permission_map.cli.map_view import render_map_summary, render_user_map
from permission_map.core.graph_engine import PermissionGraph
from permission_map.core.normalizer import normalize_entity
from permission_map.database.db import Database
from permission_map.database.repositories import fetch_records
from permission_map.importers.csv_importer import import_csv
from permission_map.utils.theme import BLUE, CYAN, MUTED_STYLE, PURPLE, WARN_STYLE, WHITE

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
    """Print a clear, grouped command reference."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style=Style(color=CYAN, bold=True), no_wrap=True)
    table.add_column(style=WHITE)

    def section(title: str) -> None:
        if table.row_count:
            table.add_row("", "")
        table.add_row(Text(title, style=Style(color=PURPLE, bold=True)), "")

    section("IMPORT DATA")
    table.add_row("import <file>", "Import and validate a CSV file")
    table.add_row("  --type <entity>", "Force the entity type")
    table.add_row("  --map <field>=<col>", "Map a source column to a field")

    section("MAP ACCESS")
    table.add_row("map", "Map users, groups, roles and permissions")
    table.add_row("map <user>", "Show a user's effective permissions and why")

    section("VIEW DATA")
    table.add_row("list users", "Show all users")
    table.add_row("list groups", "Show all groups")
    table.add_row("list roles", "Show roles with their detected type")
    table.add_row("list resources", "Show all resources")
    table.add_row("list permissions", "Show all permissions")
    table.add_row("list memberships", "Show which users belong to which groups")

    section("OTHER")
    table.add_row("dashboard", "Show the full summary screen")
    table.add_row("version", "Print the version")
    table.add_row("settings", "Show configuration and data location")
    table.add_row("clear", "Clear the screen")
    table.add_row("help / ?", "Show this reference")
    table.add_row("exit / 0", "Quit the menu")

    panel = Panel(
        table,
        title=Text("COMMANDS", style=Style(color=CYAN, bold=True)),
        subtitle=Text(
            "Tip: type commands here without the 'permission-map' prefix",
            style=MUTED_STYLE,
        ),
        border_style=CYAN,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))
    console.print(
        Text.assemble(
            ("Created by ", MUTED_STYLE),
            (__author__, Style(color=WHITE, bold=True)),
            ("  ·  ", MUTED_STYLE),
            (__linkedin_display__, Style(color=BLUE, link=__author_linkedin__)),
        ),
        justify="center",
    )


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


def _run_import(console: Console, db: Database, path_text: str) -> None:
    """Import a CSV and render the result (used by option 1 and 'import')."""
    path = path_text.strip()
    if not path:
        console.print(Text("No file given.", style=WARN_STYLE), justify="center")
        return
    result = import_csv(db, Path(path))
    render_import_result(console, result)


def handle_command(
    console: Console,
    db: Database,
    choice: str,
    input_fn: Callable[[Text], str] | None = None,
) -> bool:
    """Handle one menu choice. Return False to exit, True to continue."""
    raw_command = choice.strip()
    command = raw_command.lower()

    if command in {"0", "exit", "quit", "q"}:
        return False

    if command in {"1", "import"}:
        read = input_fn or (lambda p: console.input(p))
        path_text = read(Text.assemble(("File path: ", WHITE)))
        _run_import(console, db, path_text)
        return True

    if command.startswith("import "):
        _run_import(console, db, raw_command[7:])
        return True

    if command in {"7", "settings"}:
        _show_settings(console, db)
        return True

    if command == "version":
        console.print(f"{__app_name__} v{__version__}", justify="center")
        return True

    if command == "dashboard":
        render_dashboard(console, db)
        return True

    if command in {"help", "?"}:
        render_help(console)
        return True

    if command in {"clear", "cls"}:
        console.clear()
        return True

    if command.startswith("list"):
        entity_name = raw_command.split(" ", 1)[1].strip() if " " in raw_command else ""
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

    if command == "map" or command.startswith("map "):
        target = raw_command.split(" ", 1)[1].strip() if " " in raw_command else ""
        graph = PermissionGraph(db)
        if not target:
            render_map_summary(console, graph)
        elif not graph.has_user(target):
            console.print(Text(f"Unknown user '{target}'.", style=WARN_STYLE), justify="center")
        else:
            render_user_map(console, graph, target)
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
        Text("Type 'help' for commands, 'map' to explore access, '0' to exit.", style=MUTED_STYLE),
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
