"""Fixed startup logo for PERMISSION MAP.

A single, hand-tuned block-letter mark (``PERM``) inside a double-line frame,
followed by the full name, tagline and the three pillars of the tool. The color
stays within the brand palette so the screen never looks noisy.
"""

from __future__ import annotations

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from permission_map.utils.theme import BLUE, CYAN, GREEN, PURPLE, WHITE

# The "PERM" wordmark in block letters. Each line has the same width so the
# frame is a clean rectangle.
BLOCK: tuple[str, ...] = (
    "█████╗ ███████╗██████╗ ███╗   ███╗",
    "██╔══██╗██╔════╝██╔══██╗████╗ ████║",
    "██████╔╝█████╗  ██████╔╝██╔████╔██║",
    "██╔═══╝ ██╔══╝  ██╔══██╗██║╚██╔╝██║",
    "██║     ███████╗██║  ██║██║ ╚═╝ ██║",
)

_NAME_STYLE = Style(color=WHITE, bold=True)
_TAGLINE_STYLE = Style(color=CYAN)
_BLOCK_STYLE = Style(color=CYAN)


def _pillars() -> Text:
    return Text.assemble(
        ("IDENTITY", Style(color=BLUE, bold=True)),
        ("  •  ", Style(dim=True)),
        ("ACCESS", Style(color=GREEN, bold=True)),
        ("  •  ", Style(dim=True)),
        ("VISIBILITY", Style(color=PURPLE, bold=True)),
        justify="center",
    )


def render_logo(console: Console) -> None:
    """Print the fixed brand logo, centered on the console."""
    content = Group(
        *[Text(line, style=_BLOCK_STYLE, justify="center") for line in BLOCK],
        Text("", justify="center"),
        Text("P E R M I S S I O N   M A P", style=_NAME_STYLE, justify="center"),
        Text("ACCESS INTELLIGENCE ENGINE", style=_TAGLINE_STYLE, justify="center"),
        Text("", justify="center"),
        _pillars(),
    )
    panel = Panel(
        content,
        box=box.DOUBLE_EDGE,
        border_style=CYAN,
        padding=(1, 2),
        expand=False,
    )
    console.print(panel, justify="center")
