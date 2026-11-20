"""CSV import pipeline for PERMISSION MAP.

Reads a CSV file, detects which entity it describes, maps source columns onto
canonical fields, normalizes values, validates the result, and persists it only
when there are no blocking errors.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import ValidationError

from permission_map.core.models import ENTITY_MODELS
from permission_map.core.normalizer import (
    BOOL_FIELDS,
    CANONICAL_STATUSES,
    FIELDS,
    ImportResult,
    Issue,
    detect_entity,
    normalize_status,
    parse_bool,
    resolve_mapping,
)
from permission_map.core.role_classifier import classify_role
from permission_map.database.db import Database
from permission_map.database.repositories import existing_ids, persist
from permission_map.utils.validators import (
    validate_duplicates,
    validate_references,
    validate_required,
)

# Entity -> identifier field used for within-file duplicate detection.
KEY_FIELD = {
    "users": "user_id",
    "groups": "group_id",
    "roles": "role_id",
    "resources": "resource_id",
    "permissions": "permission_id",
}

_REFERENCE_ENTITIES = ("users", "groups", "roles", "resources", "permissions")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file into (headers, rows) with UTF-8 BOM tolerance."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = [header.strip() for header in (reader.fieldnames or [])]
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    return headers, rows


def _coerce(
    entity: str,
    record: dict,
    row_number: int,
) -> list[Issue]:
    """Normalize booleans and statuses in place; return the issues found."""
    issues: list[Issue] = []

    for field_name in BOOL_FIELDS.get(entity, ()):
        raw = record.get(field_name)
        if raw in (None, ""):
            record[field_name] = False
            continue
        parsed = parse_bool(raw)
        if parsed is None:
            issues.append(
                Issue(
                    "error",
                    f"invalid boolean value '{raw}' for '{field_name}'",
                    row=row_number,
                    field=field_name,
                )
            )
            record[field_name] = False
        else:
            record[field_name] = parsed

    if entity == "users":
        raw_status = record.get("status")
        status = normalize_status(raw_status)
        record["status"] = status
        if status not in CANONICAL_STATUSES and raw_status not in (None, ""):
            issues.append(
                Issue(
                    "warning",
                    f"unrecognized status '{raw_status}' (kept as-is)",
                    row=row_number,
                    field="status",
                )
            )

    for field_name in FIELDS[entity]:
        if field_name in BOOL_FIELDS.get(entity, ()) or field_name == "status":
            continue
        if record.get(field_name) == "":
            record[field_name] = None

    return issues


def _normalize_rows(
    entity: str,
    headers: list[str],
    rows: list[dict[str, str]],
    mapping: dict[str, str],
) -> tuple[list[dict], list[Issue]]:
    records: list[dict] = []
    issues: list[Issue] = []
    for index, row in enumerate(rows, start=2):
        record = {
            field_name: row.get(mapping[field_name]) if field_name in mapping else None
            for field_name in FIELDS[entity]
        }
        issues.extend(_coerce(entity, record, index))
        records.append(record)
    return records, issues


def import_csv(
    db: Database,
    path: Path,
    entity_type: str | None = None,
    column_overrides: dict[str, str] | None = None,
) -> ImportResult:
    """Import a CSV file into the database and return a structured result."""
    source = path.name
    result = ImportResult(entity="", path=str(path))

    if not path.exists():
        result.issues.append(Issue("error", f"file not found: {path}"))
        return result

    try:
        headers, rows = read_csv(path)
    except (OSError, csv.Error) as exc:
        result.issues.append(Issue("error", f"could not read CSV: {exc}"))
        return result

    if not headers:
        result.issues.append(Issue("error", "the file has no header row"))
        return result

    entity = entity_type or detect_entity(headers, path)
    if entity is None or entity not in ENTITY_MODELS:
        result.issues.append(
            Issue("error", "could not determine entity type; pass --type explicitly")
        )
        return result

    result.entity = entity
    result.headers = headers
    result.total_rows = len(rows)

    mapping, unmatched = resolve_mapping(headers, entity, column_overrides)
    result.mapped = mapping
    for header in unmatched:
        result.issues.append(Issue("warning", f"column '{header}' was not recognized"))

    records, issues = _normalize_rows(entity, headers, rows, mapping)
    result.issues.extend(issues)

    result.issues.extend(validate_required(records, entity))

    if entity in KEY_FIELD:
        result.issues.extend(validate_duplicates(records, entity, KEY_FIELD[entity]))

    existing = {name: existing_ids(db, name) for name in _REFERENCE_ENTITIES}
    result.issues.extend(validate_references(records, entity, existing))

    if result.errors:
        return result

    model_class = ENTITY_MODELS[entity]
    models = []
    for index, record in enumerate(records, start=2):
        record["source"] = source
        # The canonical CSV uses a descriptive key (e.g. "user_id") while the
        # Pydantic model and database use the generic "external_id".
        if entity in KEY_FIELD:
            record["external_id"] = record.pop(KEY_FIELD[entity])
        if entity == "roles":
            record["role_type"] = classify_role(
                record.get("name"), record.get("description"), bool(record.get("is_admin"))
            )
        try:
            models.append(model_class(**record))
        except ValidationError as exc:
            for error in exc.errors():
                location = ".".join(str(part) for part in error["loc"])
                result.issues.append(
                    Issue("error", f"{location}: {error['msg']}", row=index)
                )

    if result.errors:
        return result

    result.imported = persist(db, entity, models)
    return result
