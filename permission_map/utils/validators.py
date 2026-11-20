"""Input validation helpers for PERMISSION MAP.

Operate on normalized canonical records (dicts keyed by canonical field names)
and return structured :class:`Issue` objects. Validation happens before any
database write, so a file with blocking errors is never partially imported.
"""

from __future__ import annotations

from permission_map.core.normalizer import REQUIRED, Issue

# Canonical field -> foreign entity checked during import.
REFERENCES: dict[str, dict[str, str]] = {
    "memberships": {"user_id": "users", "group_id": "groups"},
    "permissions": {"resource_id": "resources"},
    "role_assignments": {"role_id": "roles", "group_id": "groups", "user_id": "users"},
    "role_permissions": {"role_id": "roles", "permission_id": "permissions"},
}


def validate_required(records: list[dict], entity: str) -> list[Issue]:
    """Flag rows missing a required field or carrying an empty required value."""
    issues: list[Issue] = []
    for index, record in enumerate(records, start=2):  # row 1 is the header
        for field_name in REQUIRED[entity]:
            value = record.get(field_name)
            if value is None or str(value).strip() == "":
                issues.append(
                    Issue(
                        "error",
                        f"missing required field '{field_name}'",
                        row=index,
                        field=field_name,
                    )
                )
    return issues


def validate_duplicates(
    records: list[dict], entity: str, key: str | tuple[str, ...]
) -> list[Issue]:
    """Flag duplicate identifier values (single or composite) within a file."""
    keys: tuple[str, ...] = (key,) if isinstance(key, str) else tuple(key)
    issues: list[Issue] = []
    seen: dict[tuple[str, ...], int] = {}
    for index, record in enumerate(records, start=2):
        value = tuple((record.get(k) or "") for k in keys)
        if not any(value):
            continue
        if value in seen:
            label = " + ".join(keys)
            issues.append(
                Issue(
                    "error",
                    f"duplicate {entity} '{label}' value {value!r} "
                    f"(already on row {seen[value]})",
                    row=index,
                )
            )
        else:
            seen[value] = index
    return issues


def validate_references(
    records: list[dict],
    entity: str,
    existing: dict[str, set[str]],
) -> list[Issue]:
    """Flag references to unknown users/groups/resources not yet imported."""
    issues: list[Issue] = []
    for field_name, foreign_entity in REFERENCES.get(entity, {}).items():
        known = existing.get(foreign_entity, set())
        for index, record in enumerate(records, start=2):
            value = record.get(field_name)
            if value is None or str(value).strip() == "":
                continue
            if value not in known:
                issues.append(
                    Issue(
                        "error",
                        f"unknown {field_name} '{value}' — import {foreign_entity} first",
                        row=index,
                        field=field_name,
                    )
                )
    return issues
