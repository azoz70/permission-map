"""Heuristic role classification for PERMISSION MAP.

Determines a role's type from its explicit ``is_admin`` flag and from keywords in
its name/description, so imported roles are immediately understandable even when
the source system does not provide a type column.
"""

from __future__ import annotations

# Canonical role types, ordered from most to least privileged.
ROLE_TYPES: tuple[str, ...] = ("admin", "privileged", "readonly", "standard")

_ADMIN_KEYWORDS: tuple[str, ...] = (
    "administrator",
    "admin",
    "superuser",
    "super user",
    "root",
    "owner",
    "sysadmin",
)

_PRIVILEGED_KEYWORDS: tuple[str, ...] = (
    "privileged",
    "power user",
    "poweruser",
    "operator",
    "elevated",
    "break glass",
    "breakglass",
    "security admin",
    "cloud admin",
)

_READONLY_KEYWORDS: tuple[str, ...] = (
    "viewer",
    "read only",
    "read-only",
    "readonly",
    "reader",
    "auditor",
    "audit",
    "guest",
    "report",
    "reporting",
)


def classify_role(
    name: str | None,
    description: str | None,
    is_admin: bool = False,
) -> str:
    """Return one of ``admin``/``privileged``/``readonly``/``standard``."""
    if is_admin:
        return "admin"

    text = f"{name or ''} {description or ''}".lower()

    if any(keyword in text for keyword in _PRIVILEGED_KEYWORDS):
        return "privileged"
    if any(keyword in text for keyword in _ADMIN_KEYWORDS):
        return "admin"
    if any(keyword in text for keyword in _READONLY_KEYWORDS):
        return "readonly"
    return "standard"
