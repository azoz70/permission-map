"""Typer CLI for PERMISSION MAP.

Exposes the command surface. Running ``permission-map`` with no arguments opens
the interactive menu; ``--help`` lists every command with examples.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from permission_map import __app_name__, __description__, __version__
from permission_map.analyzers.risk_engine import RiskEngine
from permission_map.cli.dashboard import render_dashboard
from permission_map.cli.findings_view import render_analysis_summary, render_findings
from permission_map.cli.import_view import render_import_result
from permission_map.cli.list_view import render_list, with_user_roles
from permission_map.cli.map_view import render_map_summary, render_user_map
from permission_map.cli.shell import render_help, run_shell
from permission_map.core.graph_engine import PermissionGraph
from permission_map.core.normalizer import normalize_entity
from permission_map.database.db import get_database
from permission_map.database.repositories import fetch_records, list_findings
from permission_map.importers.csv_importer import import_csv
from permission_map.utils.theme import get_theme

app = typer.Typer(
    name="permission-map",
    help=__description__,
    rich_markup_mode="rich",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
    epilog=(
        "Examples:\n"
        "  permission-map\n"
        "  permission-map import examples/users.csv\n"
        "  permission-map import data.csv --type users\n"
        "  permission-map import data.csv --map user_id=Username\n"
        "  permission-map map\n"
        "  permission-map map --user u-1002\n"
        "  permission-map analyze\n"
        "  permission-map findings --severity high\n"
        "  permission-map dashboard\n"
        "  permission-map version\n"
        "  permission-map --help"
    ),
)


def _console() -> Console:
    return Console(theme=get_theme())


def _parse_mapping(items: list[str] | None) -> dict[str, str]:
    """Parse ``--map canonical=source`` pairs into a mapping dict."""
    overrides: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise typer.BadParameter(
                f"invalid mapping '{item}'; expected canonical=source (e.g. user_id=Username)"
            )
        canonical, source = item.split("=", 1)
        overrides[canonical.strip()] = source.strip()
    return overrides


@app.callback()
def _main(ctx: typer.Context) -> None:
    """Open the interactive menu when run without a subcommand."""
    if ctx.invoked_subcommand is None:
        run_shell(_console(), get_database())


@app.command("import")
def import_data(
    file: Path = typer.Argument(..., help="CSV file to import."),
    type_: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Entity type override (users|groups|roles|resources|permissions|memberships).",
    ),
    map_: list[str] | None = typer.Option(
        None, "--map", "-m", help="Column mapping as canonical=source (repeatable)."
    ),
) -> None:
    """Import and validate a CSV file into the local database."""
    console = _console()
    database = get_database()
    overrides = _parse_mapping(map_)
    result = import_csv(database, file, entity_type=type_, column_overrides=overrides)
    render_import_result(console, result)


@app.command("list")
def list_data(
    entity: str = typer.Argument(
        ..., help="Entity to list (users|groups|roles|resources|permissions|memberships)."
    ),
) -> None:
    """List imported records of one entity as a table."""
    console = _console()
    database = get_database()
    canonical = normalize_entity(entity)
    if canonical is None:
        console.print(
            f"Unknown entity '{entity}'. Use one of: users, groups, roles, resources, "
            "permissions, memberships.",
            style="red",
        )
        raise typer.Exit(1)
    records = fetch_records(database, canonical)
    if canonical == "users":
        records = with_user_roles(records, PermissionGraph(database))
    render_list(console, canonical, records)


@app.command("map")
def map_access(
    user: str | None = typer.Option(
        None, "--user", "-u", help="Show effective permissions for this user id."
    ),
) -> None:
    """Map identity relationships and show who has access to what."""
    console = _console()
    database = get_database()
    graph = PermissionGraph(database)
    if user:
        if not graph.has_user(user):
            console.print(f"Unknown user '{user}'.", style="red")
            raise typer.Exit(1)
        render_user_map(console, graph, user)
    else:
        render_map_summary(console, graph)


@app.command()
def analyze() -> None:
    """Run the risk engine, store findings and show a summary."""
    console = _console()
    database = get_database()
    engine = RiskEngine(database)
    findings = engine.run()
    engine.persist(findings)
    render_analysis_summary(console, findings)


@app.command("findings")
def findings_command(
    severity: str | None = typer.Option(
        None, "--severity", "-s", help="Filter: critical|high|medium|low."
    ),
    user: str | None = typer.Option(None, "--user", "-u", help="Filter by user id."),
) -> None:
    """List stored risk findings."""
    console = _console()
    database = get_database()
    render_findings(console, list_findings(database, severity=severity, user=user))


@app.command("help")
def help_command() -> None:
    """Show the command reference."""
    render_help(_console())


@app.command()
def dashboard() -> None:
    """Display the access-intelligence dashboard (non-interactive)."""
    render_dashboard(_console(), get_database())


@app.command()
def version() -> None:
    """Print the installed PERMISSION MAP version."""
    _console().print(f"{__app_name__} v{__version__}")


if __name__ == "__main__":
    app()
