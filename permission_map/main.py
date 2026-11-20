"""Package entry point for ``python -m permission_map``."""

from __future__ import annotations

from permission_map.cli.commands import app


def main() -> None:
    """Run the PERMISSION MAP CLI."""
    app()


if __name__ == "__main__":
    main()
