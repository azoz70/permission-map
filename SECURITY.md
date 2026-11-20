# Security Policy

PERMISSION MAP is a **local-first, read-only** access-intelligence tool. It does
not transmit data, includes no telemetry, and never modifies external IAM
systems. Imported files are parsed, never executed.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub Security Advisories:

- https://github.com/azoz70/permission-map/security/advisories/new

Include the version, a short description, and a minimal reproduction if
possible. We aim to acknowledge reports within 72 hours.

## Scope

**In scope**

- CSV import parsing and validation
- SQLite handling and local file permissions
- Terminal rendering (Rich)
- Local file handling and path handling

**Out of scope**

- Data quality of imported files (that is a data issue, not a vulnerability)
- Vulnerabilities in third-party dependencies (please report upstream; we run
  `pip-audit` in CI)

## Security design

- **Local-first** — no network access, no telemetry, no cloud.
- **Read-only analysis** — external IAM systems are never modified.
- **No secrets** — passwords and credentials are never stored.
- **Validation before persistence** — invalid input is rejected before any
  write.
- **Restricted permissions** — the data directory and database are created with
  `0700` / `0600` permissions.
- **Safe SQL** — dynamic identifiers are limited to fixed allow-lists.

## Known limitations

- Imported CSV files are trusted to be reasonably sized; extremely large files
  may consume memory.
- CSV/formula-injection protection applies to exported reports and will be
  enforced when the reporting layer ships (Phase 6).
