"""Terminal theme for PERMISSION MAP.

Defines a single, consistent color identity used across the CLI so that the
terminal never looks crowded or random:

- cyan    — primary elements and the tool brand
- blue    — users and systems
- purple  — roles and groups
- green   — healthy permissions and success
- yellow  — warnings
- red     — critical risk

Only these colors are used; no ad-hoc color choices are scattered through the
codebase.
"""

from __future__ import annotations

from rich.style import Style
from rich.theme import Theme

CYAN = "#22d3ee"
BLUE = "#60a5fa"
PURPLE = "#a78bfa"
GREEN = "#34d399"
YELLOW = "#fbbf24"
RED = "#f87171"
GRAY = "#6b7280"
WHITE = "#e5e7eb"

_theme = Theme(
    {
        "pm.brand": CYAN,
        "pm.user": BLUE,
        "pm.role": PURPLE,
        "pm.group": PURPLE,
        "pm.ok": GREEN,
        "pm.warn": YELLOW,
        "pm.critical": RED,
        "pm.muted": GRAY,
        "pm.text": WHITE,
    }
)

# Reusable Rich styles for panels, tables and inline text.
BRAND_STYLE: Style = Style(color=CYAN, bold=True)
TEXT_STYLE: Style = Style(color=WHITE)
MUTED_STYLE: Style = Style(color=GRAY)
OK_STYLE: Style = Style(color=GREEN, bold=True)
WARN_STYLE: Style = Style(color=YELLOW, bold=True)
CRITICAL_STYLE: Style = Style(color=RED, bold=True)


def get_theme() -> Theme:
    """Return the shared Rich theme."""
    return _theme
