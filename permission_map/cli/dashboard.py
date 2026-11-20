"""Dashboard rendering for PERMISSION MAP.

Builds the startup screen: the fixed brand logo, live status lines and an
access-intelligence quick overview. Every number shown is read from the real
SQLite database — an empty database is reported as zeros, never as fabricated
sample data.
"""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map import (
    __author__,
    __author_linkedin__,
    __linkedin_display__,
    __version__,
)
from permission_map.cli.logo import render_logo
from permission_map.core.graph_engine import PermissionGraph
from permission_map.database.db import Database
from permission_map.utils.theme import (
    BLUE,
    CYAN,
    GRAY,
    GREEN,
    MUTED_STYLE,
    PURPLE,
    WHITE,
    YELLOW,
)

_BRACKET_STYLE = Style(dim=True)
_LABEL_STYLE = Style(color=CYAN)
_VALUE_STYLE = Style(color=WHITE, bold=True)
_ENGINE_STYLE = Style(color=PURPLE, bold=True)


def render_status_lines(console: Console, db: Database) -> None:
    """Print the live [SYSTEM]/[DATABASE]/[ENGINE]/[VERSION] status lines.

    Rendered as a compact two-column table so the labels and values line up
    neatly under each other instead of spreading across the terminal width.
    """
    status = db.status()
    engine_state = "READY" if status["last_analysis_at"] else "STANDBY"
    database_state = "READY" if status["initialized"] else "NOT INITIALIZED"
    database_style = (
        Style(color=GREEN, bold=True)
        if status["initialized"]
        else Style(color=YELLOW, bold=True)
    )
    entries: list[tuple[str, str, Style]] = [
        ("SYSTEM", "INITIALIZED", Style(color=CYAN, bold=True)),
        ("DATABASE", database_state, database_style),
        ("ENGINE", engine_state, _ENGINE_STYLE),
        ("VERSION", __version__, MUTED_STYLE),
    ]
    table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left", no_wrap=True)
    for label, value, style in entries:
        label_cell = Text.assemble(
            ("[ ", _BRACKET_STYLE), (label, _LABEL_STYLE), (" ]", _BRACKET_STYLE)
        )
        table.add_row(label_cell, Text(value, style=style))
    console.print(Align.center(table))


def render_attribution(console: Console) -> None:
    """Print the creator credit with a clickable LinkedIn link."""
    line = Text.assemble(
        ("Created by ", MUTED_STYLE),
        (__author__, Style(color=WHITE, bold=True)),
        ("  ·  ", MUTED_STYLE),
        (__linkedin_display__, Style(color=BLUE, link=__author_linkedin__)),
    )
    console.print(line, justify="center")


def render_overview(console: Console, db: Database) -> None:
    """Print the QUICK OVERVIEW panel with real counts from the database."""
    counts = db.counts()
    privileged = len(PermissionGraph(db).privileged_users())
    findings = db.finding_count()

    table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    table.add_column(justify="right", style=MUTED_STYLE)
    table.add_column(justify="left", style=_VALUE_STYLE)
    table.add_column(justify="right", style=MUTED_STYLE)
    table.add_column(justify="left", style=_VALUE_STYLE)
    table.add_row("USERS", f"{counts['users']:,}", "GROUPS", f"{counts['groups']:,}")
    table.add_row("ROLES", f"{counts['roles']:,}", "RESOURCES", f"{counts['resources']:,}")
    table.add_row("PRIVILEGED", f"{privileged:,}", "FINDINGS", f"{findings:,}")

    panel = Panel(
        Align.center(table),
        title=Text("QUICK OVERVIEW", style=Style(color=CYAN)),
        border_style=GRAY,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))


def _commands_panel(console: Console) -> None:
    steps = Group(
        Text("permission-map import <file> → import CSV data", style=WHITE),
        Text("permission-map list <entity> → view records", style=WHITE),
        Text("permission-map               → interactive menu", style=WHITE),
        Text("permission-map dashboard     → this summary", style=WHITE),
        Text("permission-map --help        → every command", style=WHITE),
    )
    panel = Panel(
        steps,
        title=Text("COMMANDS", style=Style(color=CYAN)),
        border_style=GRAY,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))


def render_dashboard(console: Console, db: Database) -> None:
    """Render the full non-interactive dashboard (logo + status + overview)."""
    console.print("")
    render_logo(console)
    console.print("")
    render_status_lines(console, db)
    console.print("")
    render_overview(console, db)
    console.print("")
    _commands_panel(console)
    console.print("")
    render_attribution(console)
    console.print("")


def render_app_banner(console: Console, db: Database) -> None:
    """Render the startup banner shared by the dashboard and the interactive shell."""
    console.print("")
    render_logo(console)
    console.print("")
    render_status_lines(console, db)
    console.print("")
    render_overview(console, db)
    console.print("")
    render_attribution(console)
    console.print("")


__all__ = [
    "render_dashboard",
    "render_app_banner",
    "render_status_lines",
    "render_overview",
]
