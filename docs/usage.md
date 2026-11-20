# Usage

PERMISSION MAP is a local-first command-line tool. It requires Python 3.12+.

## Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The `permission-map` entry point is now available.

## Commands

```bash
permission-map                 # open the startup dashboard
permission-map --help          # list all commands and examples
permission-map dashboard       # dashboard with live database status
permission-map dashboard --logo 3   # force a specific logo variant (0-4)
permission-map version         # print the installed version
```

Data import, analysis, mapping, comparison, review and reporting commands are
added in subsequent development phases.

## Configuration

- **Data directory** — defaults to `~/.permission-map`.
- Override it with the environment variable `PERMISSION_MAP_DATA_DIR`.
- The SQLite database lives at `<data-dir>/permission-map.db`.

## Testing

```bash
pytest
```
