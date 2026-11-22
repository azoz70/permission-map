"""Transactional account reviews with captured grant evidence."""

import json
from sqlite3 import Connection

from permission_map.database.db import Database
from permission_map.web.governance import access_inventory

DECISIONS = {"approve", "reject", "investigate"}


class CampaignConflict(ValueError):
    pass


def _text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must contain 1 to {limit} characters")
    return value.strip()


def list_campaigns(db: Database) -> list[dict]:
    with db.connection() as conn:
        return [
            dict(row) for row in conn.execute("SELECT * FROM review_campaigns ORDER BY id DESC")
        ]


def _campaign(conn: Connection, campaign_id: int):
    row = conn.execute("SELECT * FROM review_campaigns WHERE id=?", (campaign_id,)).fetchone()
    if row is None:
        raise LookupError("Campaign not found")
    return dict(row)


def _event(conn, campaign_id, kind, actor, item_id=None, previous=None, decision=None, reason=None):
    conn.execute(
        "INSERT INTO campaign_events "
        "(campaign_id, kind, actor, item_id, previous_decision, decision, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (campaign_id, kind, actor, item_id, previous, decision, reason),
    )


def create_campaign(db: Database, body: dict) -> int:
    name = _text(body.get("name"), "Campaign name", 120)
    reviewer = _text(body.get("reviewer"), "Reviewer", 120)
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        inventory = access_inventory(db, conn)
        if not inventory:
            raise CampaignConflict("Import accounts before creating a campaign")
        campaign_id = conn.execute(
            "INSERT INTO review_campaigns (name, reviewer) VALUES (?, ?)", (name, reviewer)
        ).lastrowid
        conn.executemany(
            "INSERT INTO campaign_items (campaign_id, account, evidence) VALUES (?, ?, ?)",
            ((campaign_id, user["external_id"], json.dumps(user)) for user in inventory),
        )
        _event(conn, campaign_id, "created", reviewer)
    return campaign_id


def decide(db: Database, campaign_id: int, item_id: int, body: dict) -> None:
    decision = body.get("decision")
    if not isinstance(decision, str) or decision not in DECISIONS:
        raise ValueError("Choose approve, reject or investigate")
    reason = _text(body.get("reason"), "Reason", 2000)
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        campaign = _campaign(conn, campaign_id)
        if campaign["closed_at"]:
            raise CampaignConflict("Campaign is closed")
        item = conn.execute(
            "SELECT decision, reason FROM campaign_items WHERE campaign_id=? AND id=?",
            (campaign_id, item_id),
        ).fetchone()
        if item is None:
            raise LookupError("Review item not found")
        if (item["decision"], item["reason"]) == (decision, reason):
            return
        conn.execute(
            "UPDATE campaign_items SET decision=?, reason=? WHERE id=?", (decision, reason, item_id)
        )
        _event(
            conn,
            campaign_id,
            "decided",
            campaign["reviewer"],
            item_id,
            item["decision"],
            decision,
            reason,
        )


def close_campaign(db: Database, campaign_id: int) -> None:
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        campaign = _campaign(conn, campaign_id)
        if campaign["closed_at"]:
            return
        remaining = conn.execute(
            "SELECT 1 FROM campaign_items WHERE campaign_id=? AND decision IS NULL LIMIT 1",
            (campaign_id,),
        ).fetchone()
        if remaining:
            raise CampaignConflict("Decide all items before closing")
        conn.execute(
            "UPDATE review_campaigns SET closed_at=datetime('now') WHERE id=?", (campaign_id,)
        )
        _event(conn, campaign_id, "closed", campaign["reviewer"])


def campaign_report(db: Database, campaign_id: int, limit=None, after=0, include_audit=False):
    with db.connection() as conn:
        conn.execute("BEGIN")
        campaign = _campaign(conn, campaign_id)
        counts = {"pending": 0, **dict.fromkeys(sorted(DECISIONS), 0)}
        counts.update(
            dict(
                conn.execute(
                    "SELECT coalesce(decision, 'pending'), count(*) FROM campaign_items "
                    "WHERE campaign_id=? GROUP BY decision",
                    (campaign_id,),
                ).fetchall()
            )
        )
        items = []
        for row in conn.execute(
            "SELECT id, account, evidence, decision, reason FROM campaign_items "
            "WHERE campaign_id=? AND id>? ORDER BY id LIMIT ?",
            (campaign_id, after, limit + 1 if limit is not None else -1),
        ):
            item = dict(row)
            item["evidence"] = json.loads(item["evidence"])
            items.append(item)
        next_after = None
        if limit is not None and len(items) > limit:
            items.pop()
            next_after = items[-1]["id"]
        report = {"campaign": campaign, "counts": counts, "items": items, "next_after": next_after}
        if include_audit:
            report["audit"] = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM campaign_events WHERE campaign_id=? ORDER BY id", (campaign_id,)
                )
            ]
        return report
