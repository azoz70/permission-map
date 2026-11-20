"""Generate documentation screenshots (SVG) from the real CLI renderers.

Usage:
    .venv/bin/python scripts/make_screenshots.py
"""

from __future__ import annotations

import io
import tempfile
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

try:  # optional dev dependency used to render SVG -> PNG
    import resvg_py
except ImportError:  # pragma: no cover
    resvg_py = None

from permission_map.cli.dashboard import render_dashboard
from permission_map.cli.import_view import render_import_result
from permission_map.cli.list_view import render_list
from permission_map.cli.map_view import render_map_summary, render_user_map
from permission_map.cli.shell import render_help
from permission_map.core.graph_engine import PermissionGraph
from permission_map.database.db import Database
from permission_map.database.repositories import fetch_records
from permission_map.importers.csv_importer import import_csv
from permission_map.utils.theme import get_theme

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
OUTPUT = ROOT / "docs" / "screenshots"
IMPORT_ORDER = (
    "resources",
    "users",
    "groups",
    "roles",
    "permissions",
    "memberships",
    "role_permissions",
    "role_assignments",
)


def _database() -> Database:
    data_dir = Path(tempfile.mkdtemp(prefix="pm-shots-"))
    database = Database(data_dir / "permission-map.db")
    database.initialize()
    for name in IMPORT_ORDER:
        import_csv(database, EXAMPLES / f"{name}.csv")
    return database


def _console() -> Console:
    return Console(
        record=True,
        width=100,
        force_terminal=True,
        color_system="truecolor",
        theme=get_theme(),
        file=io.StringIO(),
    )


def _save(name: str, render: Callable[[Console], None]) -> None:
    console = _console()
    render(console)
    svg_path = OUTPUT / f"{name}.svg"
    console.save_svg(str(svg_path), title=f"PERMISSION MAP — {name}")
    if resvg_py is not None:
        png = resvg_py.svg_to_bytes(
            svg_path=str(svg_path),
            zoom=2.0,
            monospace_family="Menlo",
            text_rendering="optimize_legibility",
        )
        (OUTPUT / f"{name}.png").write_bytes(png)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    database = _database()

    _save("01-startup", lambda console: render_dashboard(console, database))
    _save(
        "02-list-users",
        lambda console: render_list(console, "users", fetch_records(database, "users")),
    )
    _save(
        "03-list-roles",
        lambda console: render_list(console, "roles", fetch_records(database, "roles")),
    )
    _save(
        "04-list-memberships",
        lambda console: render_list(
            console, "memberships", fetch_records(database, "memberships")
        ),
    )

    graph = PermissionGraph(database)
    _save("07-map", lambda console: render_map_summary(console, graph))
    _save("08-user-access", lambda console: render_user_map(console, graph, "u-1002"))

    # The import screenshot adds sample users, so run it last to keep the
    # other screenshots on the clean 8-user dataset.
    _save(
        "05-import",
        lambda console: render_import_result(
            console, import_csv(database, EXAMPLES / "sample-users.csv")
        ),
    )
    _save("06-help", lambda console: render_help(console))

    count = len(list(OUTPUT.glob("*.svg")))
    print(f"Saved {count} SVG screenshots to {OUTPUT}")


if __name__ == "__main__":
    main()
