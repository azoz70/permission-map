# Data Format

PERMISSION MAP uses a unified CSV model. Organizations rarely share the same
column names, so importers map *source* columns onto *canonical* fields instead
of assuming fixed headers.

## Canonical entities

| File            | Canonical columns                                              |
| --------------- | -------------------------------------------------------------- |
| `users.csv`     | `user_id, name, email, department, job_title, status, is_privileged` |
| `groups.csv`    | `group_id, name, description`                                  |
| `roles.csv`     | `role_id, name, description, is_admin`                         |
| `permissions.csv` | `permission_id, resource_id, name, action`                   |
| `memberships.csv` | `user_id, group_id`                                          |

- `user_id`, `group_id`, `role_id`, `permission_id`, `resource_id` are stable
  external identifiers used to link records across files.
- `status` is one of `active`, `suspended`, `disabled`, `left` (a canonical
  vocabulary; source-specific values are mapped during normalization).
- `is_privileged` / `is_admin` are boolean-like (`true`/`false`, `1`/`0`,
  `yes`/`no`).

## Column mapping

Because source files use different headers, each import accepts a mapping from
source header → canonical field. For example, a source column `Username` maps to
`user_id`, and `Display Name` maps to `name`.

## Role classification

Roles are automatically classified from the `is_admin` flag and keywords in
their name/description into one of four types:

- `admin` — administrative / full-control roles
- `privileged` — elevated but not full admin (operators, security/cloud admin)
- `readonly` — viewers, auditors, readers
- `standard` — regular business roles

The detected type is stored and shown in `permission-map list roles`.

## Validation

Every import is validated before it reaches the database:

- **Missing fields** — required canonical fields must be present or mapped.
- **Invalid values** — bad booleans, malformed identifiers, out-of-range values.
- **Duplicate records** — duplicate identifiers within a file are reported.
- **Unknown references** — memberships/role assignments referencing unknown
  users, groups, roles or permissions are reported.
- **Broken relationships** — a permission whose resource does not exist.
- **Inconsistent data** — the same identifier pointing at conflicting values.

Validation failures are reported clearly and never partially written to the
database.
