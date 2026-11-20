"""Tests for the input validation helpers."""

from __future__ import annotations

from permission_map.utils.validators import (
    validate_duplicates,
    validate_references,
    validate_required,
)


def test_validate_required_flags_empty() -> None:
    records = [{"user_id": ""}, {"user_id": "u1"}]
    issues = validate_required(records, "users")
    assert len(issues) == 1
    assert issues[0].row == 2
    assert issues[0].field == "user_id"


def test_validate_duplicates_flags_repeat() -> None:
    records = [{"user_id": "u1"}, {"user_id": "u1"}, {"user_id": "u2"}]
    issues = validate_duplicates(records, "users", "user_id")
    assert len(issues) == 1
    assert issues[0].row == 3


def test_validate_references_for_memberships() -> None:
    records = [
        {"user_id": "u1", "group_id": "g1"},
        {"user_id": "uX", "group_id": "g1"},
    ]
    existing = {"users": {"u1"}, "groups": {"g1"}}
    issues = validate_references(records, "memberships", existing)
    assert len(issues) == 1
    assert "uX" in issues[0].message


def test_validate_references_for_permissions() -> None:
    records = [{"resource_id": "r1"}, {"resource_id": "rX"}]
    existing = {"resources": {"r1"}}
    issues = validate_references(records, "permissions", existing)
    assert len(issues) == 1
    assert "rX" in issues[0].message
