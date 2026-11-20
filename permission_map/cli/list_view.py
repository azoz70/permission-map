"""Terminal rendering for listing imported records."""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map.utils.theme import BLUE, CYAN, GREEN, MUTED_STYLE, RED, WHITE, YELLOW

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
        ("role_type", "Type"),
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

# Suggested import command shown when an entity has no records yet.
_IMPORT_HINT: dict[str, str] = {
    "users": "examples/users.csv",
    "groups": "examples/groups.csv",
    "roles": "examples/roles.csv",
    "resources": "examples/resources.csv",
    "permissions": "examples/permissions.csv",
    "memberships": "examples/memberships.csv",
}

_PRIVILEGED_STYLE = Style(color=RED, bold=True)
_ACTIVE_STYLE = Style(color=GREEN, bold=True)
_INACTIVE_STYLE = Style(color=YELLOW, bold=True)

_ROLE_TYPE_STYLES: dict[str, Style] = {
    "admin": Style(color=RED, bold=True),
    "privileged": Style(color=YELLOW, bold=True),
    "readonly": Style(color=BLUE),
    "standard": Style(color=WHITE),
}


def _ellipsize(value: str, max_length: int = 28) -> str:
    if len(value) <= max_length:
        return value
    keep = (max_length - 1) // 2
    return f"{value[:keep]}…{value[-keep:]}"


def _format_cell(key: str, value: object) -> str | Text:
    if key in _BOOLEAN_KEYS:
        return Text("yes", style=_PRIVILEGED_STYLE) if value else Text("no", style=MUTED_STYLE)
    if key == "role_type":
        if not value:
            return "—"
        role_type = str(value)
        return Text(role_type, style=_ROLE_TYPE_STYLES.get(role_type, MUTED_STYLE))
    if key == "status":
        status = str(value or "")
        if status == "active":
            return Text(status, style=_ACTIVE_STYLE)
        if status in {"suspended", "disabled", "left"}:
            return Text(status, style=_INACTIVE_STYLE)
        return status or "—"
    if value is None or value == "":
        return "—"
    return _ellipsize(str(value))


def render_list(console: Console, entity: str, records: list[dict]) -> None:
    """Render the records of one entity as a table, or a helpful empty state."""
    columns = _COLUMNS[entity]
    console.print("")

    if not records:
        hint = _IMPORT_HINT.get(entity, "<file>")
        console.print(
            Text(f"No {entity} found yet.", style=Style(color=YELLOW, bold=True)),
            justify="center",
        )
        console.print(
            Text(f"Import one first:  permission-map import {hint}", style=MUTED_STYLE),
            justify="center",
        )
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
        table.add_row(*(_format_cell(key, record.get(key)) for key, _ in columns))

    console.print(Align.center(table))
    console.print("")
