"""Configuration handling for PERMISSION MAP.

The tool is local-first. Its persistent state (the SQLite database) lives in a
single data directory that defaults to ``~/.permission-map`` and can be
overridden with the ``PERMISSION_MAP_DATA_DIR`` environment variable. No
external data is ever transmitted.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = ".permission-map"
DB_FILENAME = "permission-map.db"
DATA_DIR_ENV = "PERMISSION_MAP_DATA_DIR"


def data_dir() -> Path:
    """Return the directory that holds persistent PERMISSION MAP state.

    The override environment variable takes precedence, otherwise the state is
    stored under the user's home directory.
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / APP_DIR_NAME


def database_path() -> Path:
    """Return the absolute path of the SQLite database file."""
    return data_dir() / DB_FILENAME


def ensure_data_dir() -> Path:
    """Create the data directory if needed and return its path.

    The directory is restricted to the current user (0700) because it holds
    imported access data.
    """
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    return directory
