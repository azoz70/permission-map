"""Tests for the data normalization layer."""

from __future__ import annotations

from pathlib import Path

from permission_map.core.normalizer import (
    detect_entity,
    normalize_status,
    parse_bool,
    resolve_mapping,
)


def test_parse_bool() -> None:
    assert parse_bool("true") is True
    assert parse_bool("1") is True
    assert parse_bool("YES") is True
    assert parse_bool("false") is False
    assert parse_bool("0") is False
    assert parse_bool("") is False
    assert parse_bool("not-a-bool") is None


def test_normalize_status() -> None:
    assert normalize_status("Active") == "active"
    assert normalize_status("enabled") == "active"
    assert normalize_status("SUSPENDED") == "suspended"
    assert normalize_status("disabled") == "disabled"
    assert normalize_status(None) == "active"
    assert normalize_status("custom-state") == "custom-state"


def test_detect_entity_from_filename() -> None:
    assert detect_entity([], filename=Path("users.csv")) == "users"
    assert detect_entity([], filename=Path("MyPermissions.csv")) == "permissions"
    assert detect_entity([], filename=Path("groups.csv")) == "groups"


def test_detect_entity_from_columns() -> None:
    assert detect_entity(["Username", "Email", "Dept"]) == "users"
    assert detect_entity(["user_id", "group_id"]) == "memberships"


def test_resolve_mapping_uses_aliases() -> None:
    mapping, unmatched = resolve_mapping(
        ["Username", "Display Name", "Email", "Extra Column"], "users"
    )
    assert mapping["user_id"] == "Username"
    assert mapping["name"] == "Display Name"
    assert mapping["email"] == "Email"
    assert "Extra Column" in unmatched


def test_resolve_mapping_honors_overrides() -> None:
    mapping, _ = resolve_mapping(
        ["Login", "Full Name"], "users", overrides={"user_id": "Login"}
    )
    assert mapping["user_id"] == "Login"
    assert mapping["name"] == "Full Name"
