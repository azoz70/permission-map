"""Local governance services built on the existing PERMISSION MAP graph.

HR matching uses exact normalized email addresses only; ambiguous or missing
matches are explicitly flagged for manual review.
"""
from __future__ import annotations

import csv
from io import StringIO

from permission_map.core.graph_engine import PermissionGraph
from permission_map.database.db import Database


def access_inventory(db: Database) -> list[dict]:
    graph = PermissionGraph(db)
    with db.connection() as conn:
        users = {
            row["external_id"]: dict(row)
            for row in conn.execute(
                "SELECT external_id, name, email, department, status FROM users"
            )
        }
    output = []
    for uid in graph.users():
        info = graph.describe_user(uid)
        output.append({
            **users[uid],
            "privileged": info.privileged,
            "roles": info.roles,
            "groups": info.groups,
            "grants": [
                {
                    "permission": g.permission_id,
                    "resource": g.resource_id,
                    "action": g.action,
                    "direct": g.direct,
                    "path": g.path,
                }
                for g in info.grants
            ],
        })
    return output


def reconcile_hr(db: Database, csv_text: str) -> dict:
    """Read-only reconciliation; HR content is not persisted."""
    reader = csv.DictReader(StringIO(csv_text.lstrip("\ufeff")))
    required = {"employee_id", "email", "employment_status"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("HR CSV requires employee_id,email,employment_status columns")
    employees = list(reader)
    if len(employees) > 50000:
        raise ValueError("Too many HR records")
    hr_by_email: dict[str, list[dict]] = {}
    for row in employees:
        email = (row.get("email") or "").strip().casefold()
        if email:
            hr_by_email.setdefault(email, []).append(row)
    results = []
    for user in access_inventory(db):
        email = (user.get("email") or "").strip().casefold()
        matches = hr_by_email.get(email, []) if email else []
        if not matches:
            status = "unmatched"
        elif len(matches) > 1:
            status = "ambiguous"
        elif (matches[0].get("employment_status") or "").strip().casefold() in {
            "terminated", "left", "inactive", "separated"
        }:
            status = "leaver"
        else:
            status = "matched"
        results.append({
            "user_id": user["external_id"],
            "email": user.get("email"),
            "status": status,
            "privileged": user["privileged"],
            "grant_count": len(user["grants"]),
            "employee_id": matches[0].get("employee_id") if len(matches) == 1 else None,
        })
    return {
        "accounts": results,
        "totals": {
            status: sum(row["status"] == status for row in results)
            for status in ("matched", "unmatched", "ambiguous", "leaver")
        },
        "limitations": "Exact email matching only. Unmatched service accounts may be legitimate; review ownership manually.",
    }
