"""Repository layer: persists validated records into SQLite.

Every write is an idempotent upsert keyed on ``external_id`` (or an
insert-or-ignore for memberships), so re-importing the same file does not create
duplicates.
"""

from __future__ import annotations

from collections.abc import Sequence

from permission_map.core.models import (
    Group,
    Membership,
    Permission,
    Resource,
    Role,
    User,
)
from permission_map.database.db import Database

_ALLOWED_TABLES = {"users", "groups", "roles", "resources"}


def _id_map(db: Database, table: str) -> dict[str, int]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"unsafe table reference: {table}")
    with db.connection() as connection:
        rows = connection.execute(f"SELECT id, external_id FROM {table}").fetchall()
    return {row["external_id"]: row["id"] for row in rows}


def upsert_users(db: Database, users: Sequence[User]) -> int:
    if not users:
        return 0
    sql = """
        INSERT INTO users
            (external_id, name, email, department, job_title, status, is_privileged, source)
        VALUES
            (:external_id, :name, :email, :department, :job_title, :status, :is_privileged, :source)
        ON CONFLICT(external_id) DO UPDATE SET
            name = excluded.name,
            email = excluded.email,
            department = excluded.department,
            job_title = excluded.job_title,
            status = excluded.status,
            is_privileged = excluded.is_privileged,
            source = excluded.source
    """
    with db.connection() as connection:
        connection.executemany(sql, [user.model_dump() for user in users])
    return len(users)


def upsert_groups(db: Database, groups: Sequence[Group]) -> int:
    if not groups:
        return 0
    sql = """
        INSERT INTO groups (external_id, name, description, source)
        VALUES (:external_id, :name, :description, :source)
        ON CONFLICT(external_id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            source = excluded.source
    """
    with db.connection() as connection:
        connection.executemany(sql, [group.model_dump() for group in groups])
    return len(groups)


def upsert_roles(db: Database, roles: Sequence[Role]) -> int:
    if not roles:
        return 0
    sql = """
        INSERT INTO roles (external_id, name, description, is_admin, source)
        VALUES (:external_id, :name, :description, :is_admin, :source)
        ON CONFLICT(external_id) DO UPDATE SET
            name = excluded.name,
            description = excluded.description,
            is_admin = excluded.is_admin,
            source = excluded.source
    """
    with db.connection() as connection:
        connection.executemany(sql, [role.model_dump() for role in roles])
    return len(roles)


def upsert_resources(db: Database, resources: Sequence[Resource]) -> int:
    if not resources:
        return 0
    sql = """
        INSERT INTO resources (external_id, name, resource_type, source)
        VALUES (:external_id, :name, :resource_type, :source)
        ON CONFLICT(external_id) DO UPDATE SET
            name = excluded.name,
            resource_type = excluded.resource_type,
            source = excluded.source
    """
    with db.connection() as connection:
        connection.executemany(sql, [resource.model_dump() for resource in resources])
    return len(resources)


def upsert_permissions(db: Database, permissions: Sequence[Permission]) -> int:
    if not permissions:
        return 0
    resource_map = _id_map(db, "resources")
    rows = [
        (
            permission.external_id,
            resource_map[permission.resource_id],
            permission.name,
            permission.action,
            permission.source,
        )
        for permission in permissions
    ]
    sql = """
        INSERT INTO permissions (external_id, resource_id, name, action, source)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
            resource_id = excluded.resource_id,
            name = excluded.name,
            action = excluded.action,
            source = excluded.source
    """
    with db.connection() as connection:
        connection.executemany(sql, rows)
    return len(permissions)


def add_memberships(db: Database, memberships: Sequence[Membership]) -> int:
    if not memberships:
        return 0
    user_map = _id_map(db, "users")
    group_map = _id_map(db, "groups")
    rows = [
        (user_map[membership.user_id], group_map[membership.group_id], membership.source)
        for membership in memberships
    ]
    sql = """
        INSERT OR IGNORE INTO memberships (user_id, group_id, source)
        VALUES (?, ?, ?)
    """
    with db.connection() as connection:
        connection.executemany(sql, rows)
    return len(rows)


def persist(db: Database, entity: str, models: Sequence) -> int:
    """Persist validated models of the given entity type and return the count."""
    persisters = {
        "users": upsert_users,
        "groups": upsert_groups,
        "roles": upsert_roles,
        "resources": upsert_resources,
        "permissions": upsert_permissions,
        "memberships": add_memberships,
    }
    if entity not in persisters:
        raise ValueError(f"unsupported entity: {entity}")
    return persisters[entity](db, models)


def existing_ids(db: Database, entity: str) -> set[str]:
    """Return the external ids already stored for an entity."""
    if entity not in _ALLOWED_TABLES:
        return set()
    with db.connection() as connection:
        rows = connection.execute(f"SELECT external_id FROM {entity}").fetchall()
    return {row["external_id"] for row in rows}


_LIST_QUERIES: dict[str, str] = {
    "users": (
        "SELECT external_id, name, email, department, job_title, status, is_privileged "
        "FROM users ORDER BY external_id"
    ),
    "groups": "SELECT external_id, name, description FROM groups ORDER BY external_id",
    "roles": "SELECT external_id, name, description, is_admin FROM roles ORDER BY external_id",
    "resources": (
        "SELECT external_id, name, resource_type FROM resources ORDER BY external_id"
    ),
    "permissions": (
        "SELECT p.external_id AS external_id, COALESCE(r.name, r.external_id) AS resource, "
        "p.name AS name, p.action AS action "
        "FROM permissions p LEFT JOIN resources r ON r.id = p.resource_id "
        "ORDER BY p.external_id"
    ),
    "memberships": (
        "SELECT u.external_id AS user_id, g.external_id AS group_id "
        "FROM memberships m "
        "JOIN users u ON u.id = m.user_id "
        "JOIN groups g ON g.id = m.group_id "
        "ORDER BY u.external_id, g.external_id"
    ),
}


def fetch_records(db: Database, entity: str) -> list[dict]:
    """Return all records of an entity as a list of dicts for display."""
    if entity not in _LIST_QUERIES:
        raise ValueError(f"unsupported entity: {entity}")
    with db.connection() as connection:
        rows = connection.execute(_LIST_QUERIES[entity]).fetchall()
    return [dict(row) for row in rows]
