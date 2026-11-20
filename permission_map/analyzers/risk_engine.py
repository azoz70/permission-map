"""Rule-based risk engine for PERMISSION MAP.

Turns the access graph into explainable findings. Every finding carries a rule,
a severity, a confidence status (confirmed / potential), evidence and a
recommended action. High privilege alone is never treated as a violation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from permission_map.core.graph_engine import (
    PRIVILEGED_ROLE_TYPES,
    PermissionGraph,
    UserAccess,
    format_path,
)
from permission_map.database.db import Database

DORMANT_STATUSES = {"suspended", "disabled", "left"}
BROAD_GROUP_THRESHOLD = 3
EXCESSIVE_GRANT_THRESHOLD = 5

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass
class Finding:
    rule: str
    severity: str
    status: str
    user: str | None
    resource: str | None
    permission: str | None
    reason: str
    evidence: str
    recommendation: str

    @property
    def finding_id(self) -> str:
        key = f"{self.rule}|{self.user}|{self.resource}|{self.permission}"
        digest = hashlib.sha1(key.encode()).hexdigest()[:8].upper()
        return f"F-{digest}"


class RiskEngine:
    """Runs the rule set over a permission graph."""

    def __init__(self, db: Database, graph: PermissionGraph | None = None) -> None:
        self.db = db
        self.graph = graph or PermissionGraph(db)

    def run(self) -> list[Finding]:
        findings: list[Finding] = []
        for user_id in self.graph.users():
            findings.extend(self._user_rules(user_id))
        findings.extend(self._group_rules())
        findings.extend(self._permission_rules())
        unique = {finding.finding_id: finding for finding in findings}
        return sorted(
            unique.values(),
            key=lambda finding: (SEVERITY_ORDER.get(finding.severity, 9), finding.finding_id),
        )

    def _user_rules(self, user_id: str) -> list[Finding]:
        access = self.graph.describe_user(user_id)
        status = self.graph.user_status(user_id)
        findings: list[Finding] = []

        if status in DORMANT_STATUSES and access.privileged:
            findings.append(
                Finding(
                    rule="dormant_privileged",
                    severity="critical",
                    status="confirmed",
                    user=user_id,
                    resource=None,
                    permission=None,
                    reason=f"account status is '{status}' but it still has administrative access",
                    evidence=self._evidence(access),
                    recommendation="confirm deprovisioning and remove the residual admin access",
                )
            )

        if access.privileged and not self.graph.user_source_privileged(user_id):
            findings.append(
                Finding(
                    rule="privileged_undeclared",
                    severity="high",
                    status="potential",
                    user=user_id,
                    resource=None,
                    permission=None,
                    reason=(
                        "user has administrative access but is not flagged privileged in the "
                        "source"
                    ),
                    evidence=self._evidence(access),
                    recommendation="update the source privileged flag or remove the admin access",
                )
            )

        for role_id in self.graph.direct_roles(user_id):
            if self.graph.role_type(role_id) in PRIVILEGED_ROLE_TYPES:
                findings.append(
                    Finding(
                        rule="direct_admin",
                        severity="high",
                        status="potential",
                        user=user_id,
                        resource=None,
                        permission=None,
                        reason=f"role '{role_id}' is assigned directly, outside group governance",
                        evidence=f"direct → {role_id}",
                        recommendation=(
                            "move the assignment into a governed group or confirm approval"
                        ),
                    )
                )
                break

        role_types = {self.graph.role_type(role) for role in access.roles}
        if (role_types & PRIVILEGED_ROLE_TYPES) and "readonly" in role_types:
            findings.append(
                Finding(
                    rule="conflicting_role_types",
                    severity="medium",
                    status="potential",
                    user=user_id,
                    resource=None,
                    permission=None,
                    reason="user holds both administrative and read-only roles",
                    evidence="roles: " + ", ".join(access.roles),
                    recommendation="remove the redundant role and keep the least-privilege one",
                )
            )

        if len(access.grants) >= EXCESSIVE_GRANT_THRESHOLD:
            findings.append(
                Finding(
                    rule="excessive_grants",
                    severity="medium",
                    status="potential",
                    user=user_id,
                    resource=None,
                    permission=None,
                    reason=f"user has {len(access.grants)} effective permissions",
                    evidence="permissions: " + ", ".join(g.permission_id for g in access.grants),
                    recommendation="review whether every permission is still required",
                )
            )

        for group_id in access.groups:
            members = self.graph.group_members(group_id)
            if len(members) < BROAD_GROUP_THRESHOLD:
                continue
            for role_id in self.graph.group_roles(group_id):
                if self.graph.role_type(role_id) not in PRIVILEGED_ROLE_TYPES:
                    continue
                findings.append(
                    Finding(
                        rule="admin_via_broad_group",
                        severity="high",
                        status="potential",
                        user=user_id,
                        resource=None,
                        permission=None,
                        reason=(
                            f"admin role '{role_id}' reaches {len(members)} members "
                            f"through group '{group_id}'"
                        ),
                        evidence=f"{group_id} → {role_id} ({len(members)} members)",
                        recommendation=(
                            "replace the broad admin role with a narrower, auditable role"
                        ),
                    )
                )
                break

        if status == "active" and not access.groups and not access.roles:
            findings.append(
                Finding(
                    rule="orphaned_user",
                    severity="low",
                    status="potential",
                    user=user_id,
                    resource=None,
                    permission=None,
                    reason="active account is not linked to any group or role",
                    evidence="memberships=0, roles=0",
                    recommendation="verify the account is intentional; otherwise disable it",
                )
            )

        if status in DORMANT_STATUSES and (access.groups or access.roles) and not access.privileged:
            findings.append(
                Finding(
                    rule="dormant_account",
                    severity="medium",
                    status="confirmed",
                    user=user_id,
                    resource=None,
                    permission=None,
                    reason=f"account status is '{status}' but it still has group/role access",
                    evidence="groups: " + (", ".join(access.groups) or "—"),
                    recommendation="confirm the account is disabled and remove residual access",
                )
            )

        return findings

    def _group_rules(self) -> list[Finding]:
        findings: list[Finding] = []
        for group_id in self.graph.groups():
            if not self.graph.group_members(group_id):
                findings.append(
                    Finding(
                        rule="orphaned_group",
                        severity="low",
                        status="potential",
                        user=None,
                        resource=None,
                        permission=None,
                        reason=f"group '{group_id}' has no members",
                        evidence="members=0",
                        recommendation="remove the empty group or document its purpose",
                    )
                )
        return findings

    def _permission_rules(self) -> list[Finding]:
        if not self.graph.has_role_permission_links():
            return []
        findings: list[Finding] = []
        for permission_id in self.graph.unused_permissions():
            findings.append(
                Finding(
                    rule="unused_permission",
                    severity="low",
                    status="confirmed",
                    user=None,
                    resource=None,
                    permission=permission_id,
                    reason="permission is not granted by any role",
                    evidence="role links=0",
                    recommendation="remove the unused permission or attach it to the right role",
                )
            )
        return findings

    @staticmethod
    def _evidence(access: UserAccess) -> str:
        if not access.grants:
            return "no effective permissions"
        admin = [grant for grant in access.grants if grant.action == "admin"]
        chosen = admin or access.grants
        return format_path(chosen[0].path)

    def persist(self, findings: list[Finding]) -> None:
        """Replace the stored findings with the current analysis."""
        with self.db.connection() as connection:
            connection.execute("DELETE FROM findings")
            user_map = {
                row["external_id"]: row["id"]
                for row in connection.execute("SELECT id, external_id FROM users")
            }
            resource_map = {
                row["external_id"]: row["id"]
                for row in connection.execute("SELECT id, external_id FROM resources")
            }
            permission_map = {
                row["external_id"]: row["id"]
                for row in connection.execute("SELECT id, external_id FROM permissions")
            }
            rows = [
                (
                    finding.finding_id,
                    finding.severity,
                    finding.status,
                    user_map.get(finding.user) if finding.user else None,
                    resource_map.get(finding.resource) if finding.resource else None,
                    permission_map.get(finding.permission) if finding.permission else None,
                    finding.rule,
                    finding.reason,
                    finding.evidence,
                    finding.recommendation,
                )
                for finding in findings
            ]
            connection.executemany(
                "INSERT INTO findings "
                "(finding_id, severity, status, user_id, resource_id, permission_id, "
                "rule, reason, evidence, recommendation) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
