"""Tests for the CLI startup experience and the fixed brand logo."""

from __future__ import annotations

from permission_map import __version__
from permission_map.cli import logo as logo_module


def test_block_mark_has_five_lines() -> None:
    assert len(logo_module.BLOCK) == 5


def test_block_lines_are_visually_aligned() -> None:
    widths = [len(line) for line in logo_module.BLOCK]
    assert max(widths) - min(widths) <= 1, "block letter lines must be visually aligned"


def test_block_mark_uses_block_glyphs() -> None:
    joined = "".join(logo_module.BLOCK)
    assert "█" in joined


def test_version_is_a_semver_triplet() -> None:
    assert isinstance(__version__, str)
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
