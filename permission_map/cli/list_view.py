"""Terminal rendering for listing imported records."""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map.utils.theme import CYAN, MUTED_STYLE, WHITE

# Entity -> (key, header) columns shown in the terminal table. Kept compact so
# the table fits a normal terminal without truncating column values.
_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "users": (
        ("external_id", "ID"),
        ("name", "Name"),
        ("email", "Email"),
        ("status", "Status"),
        ("is_privileged", "Privileged"),
    ),
    "groups": (("external_id", "ID"), ("name", "Name"), ("description", "Description")),
    "roles": (
        ("external_id", "ID"),
        ("name", "Name"),
        ("description", "Description"),
        ("is_admin", "Admin"),
    ),
    "resources": (
        ("external_id", "ID"),
        ("name", "Name"),
        ("resource_type", "Type"),
    ),
    "permissions": (
        ("external_id", "ID"),
        ("resource", "Resource"),
        ("name", "Name"),
        ("action", "Action"),
    ),
    "memberships": (("user_id", "User"), ("group_id", "Group")),
}

_BOOLEAN_KEYS = {"is_privileged", "is_admin"}


def _ellipsize(value: str, max_length: int = 28) -> str:
    if len(value) <= max_length:
        return value
    keep = (max_length - 1) // 2
    return f"{value[:keep]}…{value[-keep:]}"


def render_list(console: Console, entity: str, records: list[dict]) -> None:
    """Render the records of one entity as a table, or a clear empty state."""
    columns = _COLUMNS[entity]
    console.print("")

    if not records:
        message = Text(f"No {entity} found — import a file first.", style=MUTED_STYLE)
        console.print(message, justify="center")
        console.print("")
        return

    table = Table(
        title=Text(f"{entity.upper()} ({len(records)})", style=Style(color=CYAN, bold=True)),
        box=box.ROUNDED,
        border_style=CYAN,
        expand=False,
    )
    for _, header in columns:
        table.add_column(header, no_wrap=True, style=WHITE)
    for record in records:
        row: list[str] = []
        for key, _ in columns:
            value = record.get(key)
            if key in _BOOLEAN_KEYS:
                value = "yes" if value else "no"
            elif value is None or value == "":
                value = "—"
            else:
                value = _ellipsize(str(value))
            row.append(value)
        table.add_row(*row)

    console.print(Align.center(table))
    console.print("")
