# PERMISSION MAP — synthetic governance demo

**All names, emails and accounts are fictional.** Do not use these as real employee records. The example.com domain is reserved for examples.

## Import order (existing CLI)

1. resources.csv
2. users.csv
3. groups.csv
4. roles.csv
5. permissions.csv
6. memberships.csv
7. role_permissions.csv
8. role_assignments.csv

Use the existing CLI import command (check `permission-map --help` and `permission-map import --help`) for these eight files. Import into a **fresh local test database**, not production. The web interface is currently read-only and does not upload files.

`hr_master.csv` is a **future integration fixture** for HR reconciliation and is **not** currently supported by the CLI import schema.

## Expected review scenarios

- u-2001: accountant with a direct ERP Administrator assignment — requires business justification.
- u-2006: terminated employee still in IT group, inheriting Cloud Administrator and VPN access.
- u-2007: unmatched service account with direct Cloud Administrator privilege. Service accounts require separate ownership review, not automatic removal.
- u-2002: privileged IT administrator, potentially legitimate; verify with the system owner.
- u-2004: developer with GitHub push access via group, expected for role.

**Do not assume these findings are automatically detected by the current engine.** Some require the planned HR matching and policy rule enhancements.

The fixtures demonstrate relationships and edge cases. A successful import is not evidence that an access review campaign or risk remediation workflow has been implemented.
