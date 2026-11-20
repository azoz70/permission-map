"""Terminal views for risk findings."""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from permission_map.analyzers.risk_engine import Finding
from permission_map.utils.theme import (
    BLUE,
    CYAN,
    GREEN,
    MUTED_STYLE,
    RED,
    WHITE,
    YELLOW,
)

_SEVERITY_STYLES: dict[str, Style] = {
    "critical": Style(color=RED, bold=True),
    "high": Style(color=YELLOW, bold=True),
    "medium": Style(color=BLUE, bold=True),
    "low": MUTED_STYLE,
}


def render_findings(console: Console, rows: list[dict]) -> None:
    """Render stored findings as a readable, explainable list."""
    console.print("")
    if not rows:
        console.print(
            Text("No findings stored. Run: permission-map analyze", style=YELLOW),
            justify="center",
        )
        console.print("")
        return

    console.print(
        Text(f"FINDINGS ({len(rows)})", style=Style(color=CYAN, bold=True)),
        justify="center",
    )
    console.print("")

    for row in rows:
        severity = row["severity"]
        header = Text.assemble(
            (row["finding_id"], MUTED_STYLE),
            ("  ", WHITE),
            (severity.upper(), _SEVERITY_STYLES.get(severity, MUTED_STYLE)),
            ("  ", WHITE),
            (row["rule"], WHITE),
            ("  ", WHITE),
            (row["user_id"] or "—", MUTED_STYLE),
            ("  ", WHITE),
            (row["permission_id"] or "", MUTED_STYLE),
        )
        console.print(header)
        console.print(Text(f"   {row['reason']}", style=WHITE))
        if severity in {"critical", "high"} and row.get("evidence"):
            console.print(Text(f"   via {row['evidence']}", style=GREEN))
        console.print("")


def render_analysis_summary(console: Console, findings: list[Finding]) -> None:
    """Render the result of an analysis run."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    summary = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    summary.add_column(style=MUTED_STYLE, justify="right")
    summary.add_column(justify="left")
    for severity in ("critical", "high", "medium", "low"):
        summary.add_row(
            severity.title(),
            Text(str(counts[severity]), style=_SEVERITY_STYLES.get(severity)),
        )
    summary.add_row("Total", Text(str(len(findings)), style=Style(color=WHITE, bold=True)))

    console.print("")
    console.print(
        Align.center(
            Panel(
                summary,
                title=Text("ANALYSIS COMPLETE", style=Style(color=CYAN, bold=True)),
                border_style=CYAN,
                box=box.ROUNDED,
                expand=False,
            )
        )
    )

    top = [finding for finding in findings if finding.severity in {"critical", "high"}][:5]
    if top:
        console.print("")
        for finding in top:
            line = Text.assemble(
                (finding.finding_id + "  ", MUTED_STYLE),
                (finding.severity.upper() + "  ", _SEVERITY_STYLES.get(finding.severity)),
                (finding.rule + "  ", WHITE),
                (finding.user or "—", MUTED_STYLE),
            )
            console.print(line, justify="center")

    console.print("")
    console.print(
        Text(
            f"Stored {len(findings)} finding(s). View all: permission-map findings",
            style=MUTED_STYLE,
        ),
        justify="center",
    )
    console.print("")
