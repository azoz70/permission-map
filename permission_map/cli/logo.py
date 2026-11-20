"""ASCII logo variants for PERMISSION MAP.

Five distinct, hand-tuned logos express the core concepts of the tool — access
mapping, identity relationships and network nodes. One variant is chosen at
random on every startup so each run feels alive, while the color stays fixed to
the brand cyan so the terminal never looks noisy.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from rich.console import Console
from rich.text import Text

from permission_map.utils.theme import CYAN, MUTED_STYLE


@dataclass(frozen=True)
class Logo:
    """A named ASCII logo variant."""

    name: str
    lines: tuple[str, ...]


LOGOS: tuple[Logo, ...] = (
    Logo(
        name="access-matrix",
        lines=(
            "╭──────────────────────────────────╮",
            "│         ACCESS  MATRIX           │",
            "│                                  │",
            "│      U     G     R     P         │",
            "│    ┌─────┬─────┬─────┬─────┐     │",
            "│    │  ●  │     │     │     │     │",
            "│    │     │  ●  │     │     │     │",
            "│    │     │     │  ●  │     │     │",
            "│    │     │     │     │  ●  │     │",
            "│    └─────┴─────┴─────┴─────┘     │",
            "╰──────────────────────────────────╯",
        ),
    ),
    Logo(
        name="identity-chain",
        lines=(
            "  ┌────────┐   ┌────────┐   ┌────────┐   ┌──────────────┐",
            "  │  USER  │──▶│ GROUP  │──▶│  ROLE  │──▶│  PERMISSION  │",
            "  └────────┘   └────────┘   └────────┘   └──────────────┘",
        ),
    ),
    Logo(
        name="network-nodes",
        lines=(
            "        ● ────────────── ●",
            "       ╱│                 │╲",
            "      ╱ │                 │ ╲",
            "     ●  │                 │  ●",
            "      ╲ │                 │ ╱",
            "       ╲│                 │╱",
            "        ● ────────────── ●",
            "            │        │",
            "            └───●────┘",
        ),
    ),
    Logo(
        name="keyhole",
        lines=(
            "        ▄▄▄▄▄▄▄▄▄",
            "      ▄▀         ▀▄",
            "     ▀   ▄▄▄▄▄   ▀",
            "     ▀   █   █   ▀",
            "     ▀   █   █   ▀",
            "      ▀▄ ▀▀▀▀▀ ▄▀",
            "          █ █",
            "          ▀ ▀",
        ),
    ),
    Logo(
        name="shield",
        lines=(
            "        ▄▄▄▄▄▄▄▄▄▄▄",
            "       █           █",
            "       █  ◉     ◉  █",
            "       █   ▄▄▄▄▄   █",
            "       █   █ █ █   █",
            "       █   ▀▀▀▀▀   █",
            "        ▀▄▄▄▄▄▄▄▄▄▀",
        ),
    ),
)


def logo_count() -> int:
    """Return the number of available logo variants."""
    return len(LOGOS)


def pick_logo(seed: int | None = None) -> tuple[int, Logo]:
    """Pick a random logo variant, returning its index and the Logo object."""
    rng = random.Random(seed)
    index = rng.randrange(len(LOGOS))
    return index, LOGOS[index]


def logo_at(index: int) -> Logo:
    """Return the logo variant at the given index (0-based)."""
    return LOGOS[index % len(LOGOS)]


def render_logo(console: Console, index: int | None = None) -> Logo:
    """Render a logo variant centered on the console and return it."""
    logo = logo_at(index) if index is not None else pick_logo()[1]
    for line in logo.lines:
        text = Text(line, style=CYAN)
        console.print(text, justify="center")
    console.print(
        Text(f"#{logo.name}", style=MUTED_STYLE),
        justify="center",
    )
    return logo


def logo_line_widths() -> Sequence[int]:
    """Return the maximum line width per variant (used in tests)."""
    return [max(len(line) for line in logo.lines) for logo in LOGOS]
