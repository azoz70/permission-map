"""Typer CLI for PERMISSION MAP.

Exposes the command surface. Running ``permission-map`` with no arguments opens
the startup dashboard; ``--help`` lists every command with examples.
"""

from __future__ import annotations

import typer
from rich.console import Console

from permission_map import __app_name__, __description__, __version__
from permission_map.cli.dashboard import render_dashboard
from permission_map.database.db import get_database
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
        "  permission-map dashboard\n"
        "  permission-map dashboard --logo 3\n"
        "  permission-map version\n"
        "  permission-map --help"
    ),
)


def _console() -> Console:
    return Console(theme=get_theme())


@app.callback()
def _main(ctx: typer.Context) -> None:
    """Open the dashboard when run without a subcommand."""
    if ctx.invoked_subcommand is None:
        render_dashboard(_console(), get_database())


@app.command()
def dashboard(
    logo: int | None = typer.Option(
        None,
        "--logo",
        "-l",
        min=0,
        max=4,
        help="Force a specific logo variant (0-4) instead of a random one.",
    ),
) -> None:
    """Display the access-intelligence dashboard and live database status."""
    render_dashboard(_console(), get_database(), logo_index=logo)


@app.command()
def version() -> None:
    """Print the installed PERMISSION MAP version."""
    _console().print(f"{__app_name__} v{__version__}")


if __name__ == "__main__":
    app()
