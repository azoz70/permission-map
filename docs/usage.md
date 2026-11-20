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
permission-map import examples/users.csv     # import + validate a CSV
permission-map dashboard       # non-interactive dashboard with live database status
permission-map version         # print the installed version
```

Inside the interactive menu, type a number to select an action, or `help` to
see the options, `settings` for configuration, and `exit`/`0` to quit. Option
`[1] Import Data` asks for a file path and imports it.

## Importing data

`permission-map import` detects the entity type from the file name (e.g.
`users.csv`, `permissions.csv`) and from the columns. Import in dependency
order: `resources` before `permissions`, and `users`/`groups` before
`memberships`.

```bash
permission-map import examples/resources.csv
permission-map import examples/users.csv
permission-map import examples/groups.csv
permission-map import examples/roles.csv
permission-map import examples/permissions.csv
permission-map import examples/memberships.csv
```

Override the detected type or map non-standard column names:

```bash
permission-map import data.csv --type users
permission-map import data.csv --map user_id=Username --map name="Display Name"
```

Every import is validated before it is written: missing fields, invalid values,
duplicate identifiers and unknown references are reported, and a file with
errors is never partially imported.

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
