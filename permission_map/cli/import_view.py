"""Terminal rendering for CSV import results."""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map.core.normalizer import ImportResult
from permission_map.utils.theme import CYAN, GREEN, MUTED_STYLE, RED, WHITE, YELLOW

_ERROR_STYLE = Style(color=RED, bold=True)
_WARN_STYLE = Style(color=YELLOW, bold=True)
_OK_STYLE = Style(color=GREEN, bold=True)


def _issues_table(title: str, issues, accent: str) -> Table:
    style = Style(color=accent, bold=True)
    table = Table(title=Text(title, style=style), box=box.ROUNDED, border_style=accent)
    table.add_column("Row", justify="right", style=MUTED_STYLE)
    table.add_column("Field", style=MUTED_STYLE)
    table.add_column("Message", style=WHITE)
    for issue in issues:
        table.add_row(
            str(issue.row) if issue.row is not None else "",
            issue.field or "",
            issue.message,
        )
    return table


def render_import_result(console: Console, result: ImportResult) -> None:
    """Render an ImportResult as a clear summary plus issue tables."""
    status_text = "OK" if result.ok else "FAILED"
    status_style = _OK_STYLE if result.ok else _ERROR_STYLE

    summary = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    summary.add_column(style=MUTED_STYLE, justify="right")
    summary.add_column(style=WHITE, justify="left")
    summary.add_row("File", result.path)
    summary.add_row("Entity", result.entity or "—")
    summary.add_row("Rows", str(result.total_rows))
    summary.add_row("Imported", str(result.imported))
    summary.add_row("Errors", str(len(result.errors)))
    summary.add_row("Warnings", str(len(result.warnings)))
    summary.add_row("Status", Text(status_text, style=status_style))

    panel = Panel(
        Align.center(summary),
        title=Text("IMPORT RESULT", style=Style(color=CYAN, bold=True)),
        border_style=CYAN,
        box=box.ROUNDED,
        expand=False,
    )
    console.print("")
    console.print(Align.center(panel))

    if result.errors:
        console.print("")
        console.print(Align.center(_issues_table("Errors", result.errors, RED)))
    if result.warnings:
        console.print("")
        console.print(Align.center(_issues_table("Warnings", result.warnings, YELLOW)))

    console.print("")
    if result.ok:
        message = Text(f"Imported {result.imported} {result.entity} record(s).", style=_OK_STYLE)
    else:
        message = Text("Nothing was written — fix the errors and re-run.", style=_ERROR_STYLE)
    console.print(message, justify="center")
    console.print("")
