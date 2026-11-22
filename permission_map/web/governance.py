"""Local governance services built on the existing PERMISSION MAP graph.

HR matching uses exact normalized email addresses only; ambiguous or missing
matches are explicitly flagged for manual review.
"""

from __future__ import annotations

import csv
from collections import Counter
from contextlib import nullcontext
from io import StringIO

from permission_map.core.graph_engine import PermissionGraph
from permission_map.database.db import Database
from permission_map.importers.csv_importer import read_tabular_rows


def access_inventory(db: Database, connection=None) -> list[dict]:
    with db.connection() if connection is None else nullcontext(connection) as conn:
        graph = PermissionGraph(db, conn)
        users = {
            row["external_id"]: dict(row)
            for row in conn.execute(
                "SELECT external_id, name, email, department, status FROM users"
            )
        }
    output = []
    for uid in graph.users():
        info = graph.describe_user(uid)
        output.append(
            {
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
            }
        )
    return output


def reconcile_hr(db: Database, csv_text: str) -> dict:
    """Read-only reconciliation; HR content is not persisted."""
    try:
        headers, employees = read_tabular_rows(
            csv.reader(StringIO(csv_text.lstrip("\ufeff")), strict=True)
        )
    except csv.Error as exc:
        raise ValueError("Invalid HR CSV") from exc
    required = {"employee_id", "email", "employment_status"}
    if not required.issubset(headers):
        raise ValueError("HR CSV requires employee_id,email,employment_status columns")
    if len(employees) > 50000:
        raise ValueError("Too many HR records")
    hr_by_email: dict[str, list[dict]] = {}
    employee_ids = Counter(row["employee_id"].casefold() for row in employees)
    for row in employees:
        email = row["email"].casefold()
        if email:
            hr_by_email.setdefault(email, []).append(row)
    active = {"active", "employed", "leave", "on leave"}
    leavers = {"terminated", "left", "inactive", "separated"}
    results = []
    for user in access_inventory(db):
        email = (user.get("email") or "").strip().casefold()
        matches = hr_by_email.get(email, []) if email else []
        if not matches:
            status = "unmatched"
        elif len(matches) > 1 or employee_ids[matches[0]["employee_id"].casefold()] > 1:
            status = "ambiguous"
        elif not matches[0]["employee_id"] or (
            matches[0]["employment_status"].casefold() not in active | leavers
        ):
            status = "invalid"
        elif matches[0]["employment_status"].casefold() in leavers:
            status = "leaver"
        else:
            status = "matched"
        results.append(
            {
                "user_id": user["external_id"],
                "email": user.get("email"),
                "status": status,
                "privileged": user["privileged"],
                "grant_count": len(user["grants"]),
                "employee_id": matches[0].get("employee_id")
                if status in {"matched", "leaver"}
                else None,
            }
        )
    return {
        "accounts": results,
        "totals": {
            status: sum(row["status"] == status for row in results)
            for status in ("matched", "unmatched", "ambiguous", "leaver", "invalid")
        },
        "limitations": (
            "Exact email matching only. Unmatched service accounts may be legitimate. "
            "Review ownership manually."
        ),
    }
