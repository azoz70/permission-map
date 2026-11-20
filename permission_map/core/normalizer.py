"""Data normalization for PERMISSION MAP.

Maps source-specific column names onto the canonical fields, normalizes values
(booleans, status), detects which entity a file describes, and reports the
issues collected during normalization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Canonical fields per entity, in import order.
FIELDS: dict[str, tuple[str, ...]] = {
    "users": ("user_id", "name", "email", "department", "job_title", "status", "is_privileged"),
    "groups": ("group_id", "name", "description"),
    "roles": ("role_id", "name", "description", "is_admin"),
    "resources": ("resource_id", "name", "resource_type"),
    "permissions": ("permission_id", "resource_id", "name", "action"),
    "memberships": ("user_id", "group_id"),
}

# Fields that must be present (and non-empty) for an entity to be importable.
REQUIRED: dict[str, tuple[str, ...]] = {
    "users": ("user_id",),
    "groups": ("group_id",),
    "roles": ("role_id",),
    "resources": ("resource_id",),
    "permissions": ("permission_id", "resource_id"),
    "memberships": ("user_id", "group_id"),
}

# Accepted synonyms for each canonical field (matched case/whitespace-insensitively).
ALIASES: dict[str, tuple[str, ...]] = {
    "user_id": ("user_id", "userid", "user id", "username", "user name", "login",
                "uid", "samaccountname", "employee id", "employeeid"),
    "group_id": ("group_id", "groupid", "group id", "groupname", "group name", "group"),
    "role_id": ("role_id", "roleid", "role id", "rolename", "role name", "role"),
    "resource_id": ("resource_id", "resourceid", "resource id", "resourcename",
                    "resource name", "resource"),
    "permission_id": ("permission_id", "permissionid", "permission id",
                      "permissionname", "permission name", "permission"),
    "name": ("name", "display name", "displayname", "full name", "fullname"),
    "email": ("email", "e-mail", "mail", "email address", "emailaddress"),
    "department": ("department", "dept", "business unit", "division"),
    "job_title": ("job_title", "job title", "title", "position"),
    "status": ("status", "account status", "accountstate", "state", "enabled"),
    "is_privileged": ("is_privileged", "privileged", "is privileged"),
    "is_admin": ("is_admin", "isadmin", "admin", "administrator"),
    "description": ("description", "desc", "notes"),
    "resource_type": ("resource_type", "resource type", "type", "kind"),
    "action": ("action", "access", "access level", "privilege"),
}

# Filename stems that unambiguously identify an entity.
STEM_TO_ENTITY: dict[str, str] = {
    "users": "users",
    "user": "users",
    "groups": "groups",
    "group": "groups",
    "roles": "roles",
    "role": "roles",
    "resources": "resources",
    "resource": "resources",
    "permissions": "permissions",
    "permission": "permissions",
    "memberships": "memberships",
    "membership": "memberships",
    "role_assignments": "role_assignments",
    "roleassignment": "role_assignments",
    "role-assignments": "role_assignments",
}

CANONICAL_STATUSES = {"active", "suspended", "disabled", "left"}

# Boolean fields per entity that must be coerced from source values.
BOOL_FIELDS: dict[str, tuple[str, ...]] = {
    "users": ("is_privileged",),
    "roles": ("is_admin",),
}

_TRUE_VALUES = {"true", "1", "yes", "y", "on", "t"}
_FALSE_VALUES = {"false", "0", "no", "n", "off", "f", ""}

# entity -> table used for reference resolution during import.
ENTITY_TO_TABLE: dict[str, str] = {
    "users": "users",
    "groups": "groups",
    "roles": "roles",
    "resources": "resources",
    "permissions": "permissions",
}


@dataclass
class Issue:
    severity: str  # "error" | "warning"
    message: str
    row: int | None = None
    field: str | None = None


@dataclass
class ImportResult:
    entity: str
    path: str
    headers: list[str] = field(default_factory=list)
    mapped: dict[str, str] = field(default_factory=dict)
    total_rows: int = 0
    imported: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


_ALIAS_TO_FIELD: dict[str, str] = {
    _norm(alias): field for field, aliases in ALIASES.items() for alias in aliases
}


def normalize_key(value: str) -> str:
    """Return the case/whitespace-insensitive key for a header or value."""
    return _norm(value)


def detect_entity(headers: list[str], filename: Path | None = None) -> str | None:
    """Determine which entity a file describes, using filename then columns."""
    if filename is not None:
        stem = _norm(filename.stem).replace(" ", "_")
        if stem in STEM_TO_ENTITY:
            return STEM_TO_ENTITY[stem]
        # Fall back to a substring match so files like "MyPermissions.csv" work.
        for key in sorted(STEM_TO_ENTITY, key=len, reverse=True):
            if key in stem:
                return STEM_TO_ENTITY[key]

    normalized = {_norm(header) for header in headers}
    best_entity: str | None = None
    best_score = 0
    for entity, fields in FIELDS.items():
        score = sum(
            1 for canonical in fields if any(_norm(a) in normalized for a in ALIASES[canonical])
        )
        if score > best_score:
            best_entity, best_score = entity, score
    return best_entity if best_score >= 1 else None


def resolve_mapping(
    headers: list[str],
    entity: str,
    overrides: dict[str, str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Map canonical fields to source headers. Returns (mapping, unmatched).

    ``overrides`` maps a canonical field to a source header (e.g.
    ``{"user_id": "Username"}``).
    """
    mapping: dict[str, str] = {}
    overrides = overrides or {}

    for canonical, source in overrides.items():
        if source in headers and canonical in FIELDS[entity]:
            mapping[canonical] = source

    unmatched: list[str] = []
    for header in headers:
        if header in mapping.values():
            continue
        canonical = _ALIAS_TO_FIELD.get(_norm(header))
        if canonical is None:
            unmatched.append(header)
            continue
        if canonical not in FIELDS[entity]:
            continue
        mapping.setdefault(canonical, header)
    return mapping, unmatched


def parse_bool(value: str | None) -> bool | None:
    """Parse a boolean-like value. Returns None when it cannot be interpreted."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return None


def normalize_status(value: str | None) -> str:
    """Normalize an account status to the canonical vocabulary."""
    if value is None or value.strip() == "":
        return "active"
    normalized = value.strip().lower()
    mapping = {"active": "active", "enabled": "active", "1": "active",
               "suspended": "suspended", "disabled": "disabled", "inactive": "disabled",
               "left": "left", "departed": "left", "terminated": "left"}
    return mapping.get(normalized, normalized)
