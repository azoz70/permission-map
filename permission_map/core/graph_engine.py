"""Identity & permission graph engine for PERMISSION MAP.

Builds a directed graph of users, groups, roles and permissions, then answers
"who has access to what — and why" by tracing the path that grants each
permission to each user.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field

import networkx as nx

from permission_map.core.role_classifier import classify_role
from permission_map.database.db import Database

PRIVILEGED_ROLE_TYPES = {"admin", "privileged"}

Node = tuple[str, str]  # (kind, external_id)


@dataclass
class Grant:
    """One effective permission and how the user obtained it."""

    permission_id: str
    permission_name: str
    action: str
    resource_id: str
    path: list[str]
    direct: bool


@dataclass
class UserAccess:
    """The effective access of one user."""

    user_id: str
    groups: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    grants: list[Grant] = field(default_factory=list)
    privileged: bool = False


class PermissionGraph:
    """A directed graph: user → group → role → permission."""

    def __init__(self, db: Database, connection=None) -> None:
        self.db = db
        self.graph: nx.DiGraph = nx.DiGraph()
        self._permission_info: dict[str, dict[str, str]] = {}
        self._role_type: dict[str, str] = {}
        self._user_status: dict[str, str] = {}
        self._user_flag: dict[str, bool] = {}
        self._build(connection)

    def _build(self, connection) -> None:
        graph = self.graph
        context = self.db.connection() if connection is None else nullcontext(connection)
        with context as connection:
            if not connection.in_transaction:
                connection.execute("BEGIN")
            users = connection.execute(
                "SELECT external_id, status, is_privileged FROM users"
            ).fetchall()
            groups = [
                row["external_id"]
                for row in connection.execute("SELECT external_id FROM groups")
            ]
            roles = connection.execute(
                "SELECT external_id, name, description, is_admin, role_type FROM roles"
            ).fetchall()
            permissions = connection.execute(
                "SELECT p.external_id, p.name, p.action, "
                "COALESCE(r.external_id, '') AS resource "
                "FROM permissions p LEFT JOIN resources r ON r.id = p.resource_id"
            ).fetchall()
            memberships = connection.execute(
                "SELECT u.external_id AS user_id, g.external_id AS group_id "
                "FROM memberships m "
                "JOIN users u ON u.id = m.user_id "
                "JOIN groups g ON g.id = m.group_id"
            ).fetchall()
            assignments = connection.execute(
                "SELECT r.external_id AS role_id, "
                "COALESCE(g.external_id, '') AS group_id, "
                "COALESCE(u.external_id, '') AS user_id "
                "FROM role_assignments ra "
                "JOIN roles r ON r.id = ra.role_id "
                "LEFT JOIN groups g ON g.id = ra.group_id "
                "LEFT JOIN users u ON u.id = ra.user_id"
            ).fetchall()
            role_permissions = connection.execute(
                "SELECT r.external_id AS role_id, p.external_id AS permission_id "
                "FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id"
            ).fetchall()

        for row in users:
            user_id = row["external_id"]
            graph.add_node(("user", user_id), kind="user")
            self._user_status[user_id] = row["status"] or "active"
            self._user_flag[user_id] = bool(row["is_privileged"])
        for group in groups:
            graph.add_node(("group", group), kind="group")
        for row in roles:
            role_id = row["external_id"]
            graph.add_node(("role", role_id), kind="role")
            self._role_type[role_id] = row["role_type"] or classify_role(
                row["name"], row["description"], bool(row["is_admin"])
            )
        for row in permissions:
            graph.add_node(("permission", row["external_id"]), kind="permission")
            self._permission_info[row["external_id"]] = {
                "name": row["name"] or row["external_id"],
                "action": row["action"] or "",
                "resource": row["resource"],
            }

        for row in memberships:
            graph.add_edge(
                ("user", row["user_id"]), ("group", row["group_id"]), relation="member"
            )
        for row in assignments:
            if row["group_id"]:
                graph.add_edge(
                    ("group", row["group_id"]), ("role", row["role_id"]), relation="assigned"
                )
            if row["user_id"]:
                graph.add_edge(
                    ("user", row["user_id"]), ("role", row["role_id"]), relation="direct"
                )
        for row in role_permissions:
            graph.add_edge(
                ("role", row["role_id"]),
                ("permission", row["permission_id"]),
                relation="grants",
            )

    # -- queries ---------------------------------------------------------
    def has_user(self, user_id: str) -> bool:
        return ("user", user_id) in self.graph

    def users(self) -> list[str]:
        return sorted(node[1] for node in self.graph.nodes if node[0] == "user")

    def groups(self) -> list[str]:
        return sorted(node[1] for node in self.graph.nodes if node[0] == "group")

    def user_status(self, user_id: str) -> str:
        return self._user_status.get(user_id, "active")

    def user_source_privileged(self, user_id: str) -> bool:
        return self._user_flag.get(user_id, False)

    def role_type(self, role_id: str) -> str:
        return self._role_type.get(role_id, "")

    def direct_roles(self, user_id: str) -> list[str]:
        """Roles assigned directly to the user (not through a group)."""
        node = ("user", user_id)
        if node not in self.graph:
            return []
        return sorted(n[1] for n in self.graph.successors(node) if n[0] == "role")

    def group_members(self, group_id: str) -> list[str]:
        node = ("group", group_id)
        if node not in self.graph:
            return []
        return sorted(n[1] for n in self.graph.predecessors(node) if n[0] == "user")

    def group_roles(self, group_id: str) -> list[str]:
        node = ("group", group_id)
        if node not in self.graph:
            return []
        return sorted(n[1] for n in self.graph.successors(node) if n[0] == "role")

    def has_role_permission_links(self) -> bool:
        return any(data.get("relation") == "grants" for _, _, data in self.graph.edges(data=True))

    def unused_permissions(self) -> list[str]:
        """Permissions that no role grants."""
        used = {
            successor[1]
            for node in self.graph.nodes
            if node[0] == "role"
            for successor in self.graph.successors(node)
            if successor[0] == "permission"
        }
        return sorted(pid for pid in self._permission_info if pid not in used)

    def user_groups(self, user_id: str) -> list[str]:
        node = ("user", user_id)
        if node not in self.graph:
            return []
        return sorted(n[1] for n in self.graph.successors(node) if n[0] == "group")

    def user_roles(self, user_id: str) -> list[str]:
        node = ("user", user_id)
        if node not in self.graph:
            return []
        roles: set[str] = set()
        for successor in self.graph.successors(node):
            if successor[0] == "role":
                roles.add(successor[1])
            elif successor[0] == "group":
                for role in self.graph.successors(successor):
                    if role[0] == "role":
                        roles.add(role[1])
        return sorted(roles)

    def describe_user(self, user_id: str) -> UserAccess:
        node = ("user", user_id)
        access = UserAccess(
            user_id=user_id,
            groups=self.user_groups(user_id),
            roles=self.user_roles(user_id),
        )
        if node not in self.graph:
            return access

        for permission_node in nx.descendants(self.graph, node):
            if permission_node[0] != "permission":
                continue
            path = nx.shortest_path(self.graph, node, permission_node)
            info = self._permission_info.get(permission_node[1], {})
            access.grants.append(
                Grant(
                    permission_id=permission_node[1],
                    permission_name=info.get("name", permission_node[1]),
                    action=info.get("action", ""),
                    resource_id=info.get("resource", ""),
                    path=[f"{kind}:{ext}" for kind, ext in path],
                    direct=len(path) > 1 and path[1][0] == "role",
                )
            )

        access.grants.sort(key=lambda grant: (grant.resource_id, grant.permission_id))
        access.privileged = (
            self._user_flag.get(user_id, False)
            or any(
                self._role_type.get(role) in PRIVILEGED_ROLE_TYPES for role in access.roles
            )
            or any(grant.action == "admin" for grant in access.grants)
        )
        return access

    def privileged_users(self) -> list[str]:
        users = sorted(node[1] for node in self.graph.nodes if node[0] == "user")
        return [user for user in users if self.describe_user(user).privileged]

    def role_rows(self) -> list[dict]:
        """Return role-level mapping rows for the summary view."""
        rows: list[dict] = []
        for node in self.graph.nodes:
            if node[0] != "role":
                continue
            role_id = node[1]
            permissions = [n[1] for n in self.graph.successors(node) if n[0] == "permission"]
            assigned = [
                predecessor
                for predecessor in self.graph.predecessors(node)
                if predecessor[0] in {"group", "user"}
            ]
            rows.append(
                {
                    "role_id": role_id,
                    "role_type": self._role_type.get(role_id, ""),
                    "permissions": len(permissions),
                    "assigned": len(assigned),
                }
            )
        return sorted(rows, key=lambda row: row["role_id"])

    def summary(self) -> dict[str, int]:
        relation_counts: dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            relation = data.get("relation", "other")
            relation_counts[relation] = relation_counts.get(relation, 0) + 1
        return {
            "users": sum(1 for node in self.graph.nodes if node[0] == "user"),
            "groups": sum(1 for node in self.graph.nodes if node[0] == "group"),
            "roles": sum(1 for node in self.graph.nodes if node[0] == "role"),
            "permissions": sum(1 for node in self.graph.nodes if node[0] == "permission"),
            "memberships": relation_counts.get("member", 0),
            "role_assignments": relation_counts.get("assigned", 0)
            + relation_counts.get("direct", 0),
            "role_permissions": relation_counts.get("grants", 0),
            "privileged_users": len(self.privileged_users()),
        }


def format_path(path: list[str]) -> str:
    """Format a ``kind:id`` node path as a readable chain."""
    return " → ".join(node.split(":", 1)[1] for node in path)
