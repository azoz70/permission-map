"""Tests for heuristic role classification."""

from __future__ import annotations

from permission_map.core.role_classifier import ROLE_TYPES, classify_role


def test_role_types_constant() -> None:
    assert set(ROLE_TYPES) == {"admin", "privileged", "readonly", "standard"}


def test_admin_by_flag() -> None:
    assert classify_role("Reader", None, is_admin=True) == "admin"


def test_admin_by_name() -> None:
    assert classify_role("Administrator", "full access") == "admin"
    assert classify_role("Root", None) == "admin"
    assert classify_role("System Administrator", None) == "admin"


def test_privileged() -> None:
    assert classify_role("Security Admin", None) == "privileged"
    assert classify_role("Power User", None) == "privileged"
    assert classify_role("Cloud Operator", None) == "privileged"


def test_readonly() -> None:
    assert classify_role("Viewer", "read-only access") == "readonly"
    assert classify_role("Finance Reader", "read financial reports") == "readonly"
    assert classify_role("Auditor", None) == "readonly"


def test_standard() -> None:
    assert classify_role("Developer", "code and deploy access") == "standard"
    assert classify_role("Security Analyst", "investigate access") == "standard"
