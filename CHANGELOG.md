# Changelog

All notable changes to PERMISSION MAP are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-11-20

### Added

- Rule-based risk engine with explainable findings: `dormant_privileged`,
  `privileged_undeclared`, `direct_admin`, `admin_via_broad_group`,
  `conflicting_role_types`, `excessive_grants`, `orphaned_user`,
  `orphaned_group`, `unused_permission`, `dormant_account`.
- `permission-map analyze` runs the rules, stores findings and shows a summary.
- `permission-map findings` lists findings, filterable by `--severity` and
  `--user`.
- Each finding has a stable ID, severity, confidence (confirmed/potential),
  evidence (grant path) and a recommended action.
- Dashboard now reports inferred privileged users and stored findings.
- 62 tests and two new screenshots.

## [0.2.1] - 2026-11-20

### Changed

- `list users` now shows each user's effective roles (compacted with `+N` for
  many roles) and marks privilege from both the source flag and inferred admin
  access, so roles are no longer a separate lookup.

## [0.2.0] - 2026-11-20

### Added

- Identity & permission graph engine (`core/graph_engine.py`): user → group →
  role → permission, with effective-permission resolution and grant paths.
- `permission-map map` — access-graph summary, role map and privileged users.
- `permission-map map --user <id>` — a user's effective permissions and the
  exact path that grants each one (direct vs. inherited).
- Import support for `role_assignments.csv` and `role_permissions.csv`,
  including reference and duplicate validation.
- Role-type-aware privilege inference (admin/privileged roles or admin
  permissions), replacing reliance on the source flag alone.
- `role_permissions` table (schema v3) with safe migrations.
- New example files and graph tests (56 tests total).

## [0.1.0] - 2026-11-20

### Added

- Project skeleton with a layered architecture (CLI, import, normalization,
  graph, analysis, review, reporting, database).
- CLI startup experience powered by Typer + Rich.
- Five randomized ASCII logo variants (access matrix, identity chain, network
  nodes, keyhole, shield).
- `permission-map` entry point with `dashboard` and `version` commands.
- Live database-status and access-intelligence dashboard that reads real SQLite
  state.
- SQLite schema for users, groups, roles, resources, permissions, memberships,
  role assignments, snapshots, findings, access reviews and audit logs.
- Sample CSV files and initial test suite.
