# Changelog

All notable changes to PERMISSION MAP are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
