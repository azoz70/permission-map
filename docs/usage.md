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
permission-map list users      # view imported records as a table
permission-map list memberships # view user ↔ group relationships
permission-map map             # access-graph summary, role map, privileged users
permission-map map --user u-1002  # one user's effective permissions and why
permission-map analyze         # run the risk rules and store findings
permission-map findings        # list stored findings
permission-map findings --severity critical
permission-map dashboard       # non-interactive dashboard with live database status
permission-map version         # print the installed version
permission-map help            # command reference
```

Inside the interactive menu, type a number to select an action, or `help` to
see the options, `settings` for configuration, and `exit`/`0` to quit. Option
`[1] Import Data` asks for a file path and imports it.

## Shortcuts (no repeated prefix)

Run `permission-map` once and stay inside the interactive menu — commands are
typed there **without** the `permission-map` prefix:

```text
permission-map
permission-map > import examples/users.csv
permission-map > list users
permission-map > list roles
permission-map > map
permission-map > 0
```

To shorten it from your normal shell, add an alias:

```bash
alias pm="permission-map"     # add to ~/.zshrc to keep it
pm list users
pm import examples/users.csv
```

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
permission-map import examples/role_permissions.csv
permission-map import examples/role_assignments.csv
```

Override the detected type or map non-standard column names:

```bash
permission-map import data.csv --type users
permission-map import data.csv --map user_id=Username --map name="Display Name"
```

Every import is validated before it is written: missing fields, invalid values,
duplicate identifiers and unknown references are reported, and a file with
errors is never partially imported.

## Mapping access

`role_permissions.csv` links roles to permissions and `role_assignments.csv`
assigns roles to groups or directly to users. Together with memberships they
form the access graph `user → group → role → permission`.

```bash
permission-map map                 # graph summary + role map + privileged users
permission-map map --user u-1002   # effective permissions and the path that grants each
```

The user view shows whether each grant is **direct** (role assigned to the user)
or **inherited** (via a group), plus the exact chain, e.g.
`g-itops → r-admin → p-aws-admin`.

## Risk analysis

`permission-map analyze` runs the rule engine and stores explainable findings:

```bash
permission-map analyze
permission-map findings
permission-map findings --severity critical
permission-map findings --user u-1002
```

Every finding carries a stable ID, severity (`critical`/`high`/`medium`/`low`),
confidence (`confirmed`/`potential`), the evidence path and a recommended
action. Rules include dormant privileged accounts, undeclared admin access,
direct admin assignments, admin roles on broad groups, conflicting role types,
excessive grants, orphaned users/groups and unused permissions.

Findings are derived data: re-running `analyze` replaces the stored set.

## Configuration

- **Data directory** — defaults to `~/.permission-map`.
- Override it with the environment variable `PERMISSION_MAP_DATA_DIR`.
- The SQLite database lives at `<data-dir>/permission-map.db`.

## Testing

```bash
pytest
```
