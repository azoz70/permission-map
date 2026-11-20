"""SQLite database layer for PERMISSION MAP.

Owns the schema, connection management and low-level reads used by the CLI and
the analysis layers. All persistence is local SQLite; nothing leaves the host.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from permission_map.utils import config

SCHEMA_VERSION = 3

# Order matters: parent tables must be created before tables that reference
# them with foreign keys.
_SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS metadata (
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id   TEXT NOT NULL UNIQUE,
        name          TEXT,
        email         TEXT,
        department    TEXT,
        job_title     TEXT,
        status        TEXT NOT NULL DEFAULT 'active',
        is_privileged INTEGER NOT NULL DEFAULT 0,
        source        TEXT,
        imported_at   TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS groups (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT NOT NULL UNIQUE,
        name        TEXT,
        description TEXT,
        source      TEXT,
        imported_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT NOT NULL UNIQUE,
        name        TEXT,
        description TEXT,
        is_admin    INTEGER NOT NULL DEFAULT 0,
        role_type   TEXT,
        source      TEXT,
        imported_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS resources (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id   TEXT NOT NULL UNIQUE,
        name          TEXT,
        resource_type TEXT,
        source        TEXT,
        imported_at   TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS permissions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        external_id TEXT NOT NULL UNIQUE,
        resource_id INTEGER REFERENCES resources(id) ON DELETE CASCADE,
        name        TEXT,
        action      TEXT,
        source      TEXT,
        imported_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memberships (
        user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
        source   TEXT,
        PRIMARY KEY (user_id, group_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_assignments (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id   INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        group_id  INTEGER REFERENCES groups(id) ON DELETE CASCADE,
        user_id   INTEGER REFERENCES users(id) ON DELETE CASCADE,
        direct    INTEGER NOT NULL DEFAULT 0,
        source    TEXT,
        imported_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
        permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
        PRIMARY KEY (role_id, permission_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        label       TEXT NOT NULL,
        description TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS snapshot_grants (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id             INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
        user_external_id        TEXT NOT NULL,
        permission_external_id  TEXT NOT NULL,
        origin                  TEXT,
        source                  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS findings (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id     TEXT NOT NULL UNIQUE,
        severity       TEXT NOT NULL,
        status         TEXT NOT NULL DEFAULT 'open',
        user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
        resource_id    INTEGER REFERENCES resources(id) ON DELETE SET NULL,
        permission_id  INTEGER REFERENCES permissions(id) ON DELETE SET NULL,
        rule           TEXT,
        reason         TEXT,
        evidence       TEXT,
        recommendation TEXT,
        created_at     TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS access_reviews (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id     TEXT NOT NULL UNIQUE,
        user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
        resource_id   INTEGER REFERENCES resources(id) ON DELETE SET NULL,
        permission_id INTEGER REFERENCES permissions(id) ON DELETE SET NULL,
        decision      TEXT NOT NULL,
        reviewer      TEXT,
        reason        TEXT,
        reviewed_at   TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type  TEXT NOT NULL,
        description TEXT,
        details     TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
)

_ENTITY_TABLES: tuple[str, ...] = (
    "users",
    "groups",
    "roles",
    "resources",
    "permissions",
)


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    """Return the column names of a table."""
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _ensure_column(
    connection: sqlite3.Connection, table: str, column: str, ddl: str
) -> None:
    """Add a column to an existing table when it is missing (safe migration)."""
    if column not in _column_names(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _restrict_permissions(path: Path, mode: int) -> None:
    """Best-effort restriction of local files that hold access data."""
    try:
        path.chmod(mode)
    except OSError:
        pass


class Database:
    """Manages the PERMISSION MAP SQLite database."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else config.database_path()

    def connect(self) -> sqlite3.Connection:
        """Open a connection with foreign keys and sane settings enabled."""
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection and commit on success, rollback on failure."""
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def exists(self) -> bool:
        """Return True when the database file already exists on disk."""
        return self.path.exists()

    def initialize(self) -> None:
        """Create the schema and stamp the schema version (idempotent)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _restrict_permissions(self.path.parent, 0o700)
        with self.connection() as connection:
            for statement in _SCHEMA:
                connection.execute(statement)
            # Safe migrations for databases created by earlier versions.
            _ensure_column(connection, "roles", "role_type", "role_type TEXT")
            connection.execute(
                "INSERT INTO metadata (key, value) VALUES ('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(SCHEMA_VERSION),),
            )
        _restrict_permissions(self.path, 0o600)

    def ensure_initialized(self) -> None:
        """Initialize the database if it has not been initialized yet."""
        self.initialize()

    def schema_version(self) -> int | None:
        """Return the stored schema version, or None when uninitialized."""
        if not self.exists():
            return None
        with self.connection() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
        return int(row["value"]) if row else None

    def counts(self) -> dict[str, int]:
        """Return the real row count of every identity/permission table."""
        if not self.exists():
            return {table: 0 for table in _ENTITY_TABLES}
        result: dict[str, int] = {}
        with self.connection() as connection:
            for table in _ENTITY_TABLES:
                row = connection.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
                result[table] = int(row["n"])
        return result

    def last_analysis_at(self) -> str | None:
        """Return the timestamp of the most recent analysis, or None."""
        if not self.exists():
            return None
        with self.connection() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'last_analysis_at'"
            ).fetchone()
        return row["value"] if row else None

    def privileged_user_count(self) -> int:
        """Return the number of users flagged as privileged."""
        if not self.exists():
            return 0
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM users WHERE is_privileged = 1"
            ).fetchone()
        return int(row["n"])

    def open_finding_count(self) -> int:
        """Return the number of open findings."""
        if not self.exists():
            return 0
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM findings WHERE status = 'open'"
            ).fetchone()
        return int(row["n"])

    def status(self) -> dict:
        """Return a snapshot of database state for the dashboard.

        Values are read from the real database; an uninitialized database is
        reported honestly rather than as a fabricated empty result.
        """
        return {
            "path": str(self.path),
            "initialized": self.exists(),
            "schema_version": self.schema_version(),
            "last_analysis_at": self.last_analysis_at(),
            "counts": self.counts(),
        }


def get_database(path: Path | str | None = None) -> Database:
    """Return an initialized Database instance (the CLI default)."""
    database = Database(path)
    database.ensure_initialized()
    return database
