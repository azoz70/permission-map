"""Tests for the CLI startup experience and logo variants."""

from __future__ import annotations

from permission_map import __version__
from permission_map.cli import logo as logo_module


def test_there_are_exactly_five_logo_variants() -> None:
    assert logo_module.logo_count() == 5
    assert len(logo_module.LOGOS) == 5


def test_every_logo_has_name_and_content() -> None:
    for logo in logo_module.LOGOS:
        assert logo.name, "each logo must be named"
        assert logo.lines, "each logo must have lines"
        assert all(line.strip() for line in logo.lines), "logo lines must not be blank"


def test_pick_logo_returns_valid_variant() -> None:
    for _ in range(200):
        index, logo = logo_module.pick_logo()
        assert 0 <= index < 5
        assert logo is logo_module.LOGOS[index]


def test_pick_logo_is_deterministic_for_a_seed() -> None:
    first = logo_module.pick_logo(seed=42)
    second = logo_module.pick_logo(seed=42)
    assert first == second


def test_logo_at_wraps_around() -> None:
    assert logo_module.logo_at(5) is logo_module.LOGOS[0]
    assert logo_module.logo_at(-1) is logo_module.LOGOS[4]


def test_version_is_a_semver_triplet() -> None:
    assert isinstance(__version__, str)
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
