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
permission-map                 # open the interactive menu (brand banner + actions)
permission-map --help          # list all commands and examples
permission-map dashboard       # non-interactive dashboard with live database status
permission-map version         # print the installed version
```

Inside the interactive menu, type a number to select an action, or `help` to
see the options, `settings` for configuration, and `exit`/`0` to quit.

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
