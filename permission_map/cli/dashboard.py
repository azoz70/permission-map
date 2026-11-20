"""Dashboard rendering for PERMISSION MAP.

Builds the startup experience: a randomized logo, brand header, live database
status and an access-intelligence summary. Every number shown is read from the
real SQLite database — an empty database is reported as zeros plus a clear
hint, never as fabricated sample data.
"""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from permission_map import __app_name__, __version__
from permission_map.cli import logo as logo_module
from permission_map.database.db import Database
from permission_map.utils.theme import (
    BRAND_STYLE,
    CYAN,
    GRAY,
    MUTED_STYLE,
    OK_STYLE,
    PURPLE,
    TEXT_STYLE,
    WARN_STYLE,
    WHITE,
)


def _thousands(value: int) -> str:
    return f"{value:,}"


def _ellipsize(value: str, max_length: int = 72) -> str:
    """Shorten long values with a middle ellipsis to keep tables tidy."""
    if len(value) <= max_length:
        return value
    keep = (max_length - 1) // 2
    return f"{value[:keep]}…{value[-keep:]}"


def _key_value_table() -> Table:
    table = Table(show_header=False, box=None, padding=(0, 0, 0, 2))
    table.add_column("label", style=MUTED_STYLE, justify="left", no_wrap=True)
    table.add_column("value", style=TEXT_STYLE, justify="left", no_wrap=True)
    return table


def _brand_header(console: Console) -> None:
    name = Text(__app_name__, style=BRAND_STYLE)
    console.print(name, justify="center")
    console.print(
        Text("ACCESS INTELLIGENCE & REVIEW ENGINE", style=CYAN),
        justify="center",
    )
    console.print(
        Text(
            f"v{__version__}  •  local-first  •  read-only analysis  •  no telemetry",
            style=MUTED_STYLE,
        ),
        justify="center",
    )
    console.print("")


def _database_panel(console: Console, db: Database) -> None:
    status = db.status()
    table = _key_value_table()
    table.add_row("Path", _ellipsize(status["path"], 46))
    table.add_row(
        "Schema",
        f"v{status['schema_version']}" if status["schema_version"] else "not initialized",
    )
    if status["initialized"]:
        table.add_row("Status", "initialized", style=OK_STYLE)
    else:
        table.add_row("Status", "not initialized", style=WARN_STYLE)
    table.add_row("Last analysis", status["last_analysis_at"] or "never")
    panel = Panel(
        table,
        title="[pm.brand]DATABASE[/pm.brand]",
        border_style=CYAN,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))
    console.print("")


def _summary_panel(console: Console, db: Database) -> None:
    counts = db.status()["counts"]
    findings = _finding_summary(db)
    snapshots = _snapshot_count(db)
    reviews = _review_count(db)

    body = _key_value_table()
    body.add_row("Total Users", _thousands(counts["users"]))
    body.add_row("Total Groups", _thousands(counts["groups"]))
    body.add_row("Total Roles", _thousands(counts["roles"]))
    body.add_row("Total Resources", _thousands(counts["resources"]))
    body.add_row("Total Permissions", _thousands(counts["permissions"]))
    body.add_row("", "")
    body.add_row("Critical Findings", _thousands(findings["critical"]))
    body.add_row("High Risk", _thousands(findings["high"]))
    body.add_row("Review Required", _thousands(findings["review"]))
    body.add_row("", "")
    body.add_row("Access Snapshots", _thousands(snapshots))
    body.add_row("Reviews Recorded", _thousands(reviews))

    panel = Panel(
        body,
        title="[pm.brand]ACCESS INTELLIGENCE[/pm.brand]",
        border_style=PURPLE,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))
    console.print("")


def _next_steps(console: Console) -> None:
    steps = Group(
        Text("import data  →  permission-map import <file>", style=WHITE),
        Text("analyze      →  permission-map analyze", style=WHITE),
        Text("map access   →  permission-map map", style=WHITE),
        Text("compare      →  permission-map compare --baseline a --current b", style=WHITE),
        Text("full help    →  permission-map --help", style=WHITE),
    )
    panel = Panel(
        steps,
        title="[pm.warn]NEXT STEPS[/pm.warn]",
        border_style=GRAY,
        box=box.ROUNDED,
        expand=False,
    )
    console.print(Align.center(panel))
    console.print("")


def _finding_summary(db: Database) -> dict[str, int]:
    """Count findings by severity bucket from the real findings table."""
    result = {"critical": 0, "high": 0, "review": 0}
    if not db.exists():
        return result
    with db.connection() as connection:
        rows = connection.execute(
            "SELECT severity, COUNT(*) AS n FROM findings GROUP BY severity"
        ).fetchall()
    for row in rows:
        severity = (row["severity"] or "").lower()
        if severity == "critical":
            result["critical"] = int(row["n"])
        elif severity == "high":
            result["high"] = int(row["n"])
        elif severity in {"medium", "review"}:
            result["review"] += int(row["n"])
    return result


def _snapshot_count(db: Database) -> int:
    if not db.exists():
        return 0
    with db.connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS n FROM snapshots").fetchone()
    return int(row["n"])


def _review_count(db: Database) -> int:
    if not db.exists():
        return 0
    with db.connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS n FROM access_reviews").fetchone()
    return int(row["n"])


def render_dashboard(console: Console, db: Database, logo_index: int | None = None) -> None:
    """Render the full startup dashboard."""
    console.print("")
    logo_module.render_logo(console, index=logo_index)
    console.print("")
    _brand_header(console)
    _database_panel(console, db)
    _summary_panel(console, db)
    _next_steps(console)
