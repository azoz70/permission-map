"""Terminal views for the access map (identity → permission graph)."""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map.core.graph_engine import PermissionGraph
from permission_map.utils.theme import (
    BLUE,
    CYAN,
    GREEN,
    MUTED_STYLE,
    RED,
    WHITE,
    YELLOW,
)

_ROLE_TYPE_STYLES: dict[str, Style] = {
    "admin": Style(color=RED, bold=True),
    "privileged": Style(color=YELLOW, bold=True),
    "readonly": Style(color=BLUE),
    "standard": Style(color=WHITE),
}


def _via_chain(path: list[str]) -> str:
    """Return the group/role chain that grants access (without user/permission)."""
    middle = path[1:-1]
    return " → ".join(node.split(":", 1)[1] for node in middle) or "—"


def render_map_summary(console: Console, graph: PermissionGraph) -> None:
    """Render the overall identity/permission mapping summary."""
    summary = graph.summary()
    console.print("")

    counts = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    counts.add_column(style=MUTED_STYLE, justify="right")
    counts.add_column(style=WHITE, justify="left")
    counts.add_row("Users", str(summary["users"]))
    counts.add_row("Groups", str(summary["groups"]))
    counts.add_row("Roles", str(summary["roles"]))
    counts.add_row("Permissions", str(summary["permissions"]))
    counts.add_row("Memberships", str(summary["memberships"]))
    counts.add_row("Role assignments", str(summary["role_assignments"]))
    counts.add_row("Role → permission links", str(summary["role_permissions"]))
    counts.add_row("Privileged users", str(summary["privileged_users"]))

    console.print(
        Align.center(
            Panel(
                counts,
                title=Text("ACCESS GRAPH", style=Style(color=CYAN, bold=True)),
                border_style=CYAN,
                box=box.ROUNDED,
                expand=False,
            )
        )
    )

    rows = graph.role_rows()
    if rows:
        console.print("")
        table = Table(
            title=Text("ROLE MAP", style=Style(color=CYAN, bold=True)),
            box=box.ROUNDED,
            border_style=CYAN,
            expand=False,
        )
        table.add_column("Role", no_wrap=True, style=WHITE)
        table.add_column("Type", no_wrap=True)
        table.add_column("Permissions", justify="right", style=WHITE)
        table.add_column("Assigned", justify="right", style=WHITE)
        for row in rows:
            role_type = row["role_type"]
            table.add_row(
                row["role_id"],
                Text(role_type or "—", style=_ROLE_TYPE_STYLES.get(role_type, MUTED_STYLE)),
                str(row["permissions"]),
                str(row["assigned"]),
            )
        console.print(Align.center(table))

    privileged = graph.privileged_users()
    console.print("")
    if privileged:
        message = Text.assemble(
            (f"{len(privileged)} privileged user(s): ", Style(color=RED, bold=True)),
            (", ".join(privileged), WHITE),
        )
    else:
        message = Text(
            "No privileged users detected (import roles, role_permissions and "
            "role_assignments to map access).",
            style=MUTED_STYLE,
        )
    console.print(message, justify="center")
    console.print("")


def render_user_map(console: Console, graph: PermissionGraph, user_id: str) -> None:
    """Render one user's effective permissions and the path that grants them."""
    access = graph.describe_user(user_id)
    console.print("")

    header = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    header.add_column(style=MUTED_STYLE, justify="right")
    header.add_column(style=WHITE, justify="left")
    header.add_row("User", access.user_id)
    header.add_row("Groups", ", ".join(access.groups) or "—")
    header.add_row("Roles", ", ".join(access.roles) or "—")
    header.add_row(
        "Privileged",
        Text("yes", style=Style(color=RED, bold=True))
        if access.privileged
        else Text("no", style=MUTED_STYLE),
    )
    console.print(
        Align.center(
            Panel(
                header,
                title=Text("USER ACCESS", style=Style(color=CYAN, bold=True)),
                border_style=CYAN,
                box=box.ROUNDED,
                expand=False,
            )
        )
    )

    if not access.grants:
        console.print("")
        console.print(
            Text(
                "No effective permissions. Import role_permissions.csv and "
                "role_assignments.csv to map access.",
                style=YELLOW,
            ),
            justify="center",
        )
        console.print("")
        return

    console.print("")
    table = Table(
        title=Text("EFFECTIVE PERMISSIONS", style=Style(color=CYAN, bold=True)),
        box=box.ROUNDED,
        border_style=CYAN,
        expand=False,
    )
    table.add_column("Permission", no_wrap=True, style=WHITE)
    table.add_column("Resource", no_wrap=True, style=WHITE)
    table.add_column("Action", no_wrap=True)
    table.add_column("Via", style=MUTED_STYLE)
    table.add_column("Path", style=GREEN)
    for grant in access.grants:
        action_style = Style(color=RED, bold=True) if grant.action == "admin" else WHITE
        table.add_row(
            grant.permission_id,
            grant.resource_id or "—",
            Text(grant.action or "—", style=action_style),
            "direct" if grant.direct else "inherited",
            _via_chain(grant.path),
        )
    console.print(Align.center(table))
    console.print("")
