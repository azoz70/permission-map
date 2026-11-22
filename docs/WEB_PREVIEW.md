# Local governance web interface

Install the project and run `python -m permission_map.web.app`. Open
<http://127.0.0.1:8765>. To isolate a run from CLI data, set
`PERMISSION_MAP_DATA_DIR` to a dedicated directory before starting. Otherwise
the web app and CLI use the same local SQLite database.

## Access data and HR reconciliation

Import access entities in dependency order: resources, users, groups, roles,
permissions, memberships, role permissions, and role assignments. The web
interface accepts UTF-8 CSV and single-sheet XLSX. Use a header row and store
identifiers with leading zeroes as text. XLSX supports up to 50,000 data rows,
64 columns, and 32 MiB of expanded archive data. Formula and error cells
are rejected. The HTTP request limit is 8 MiB, including JSON and any base64
encoding. Validation errors prevent the batch from being saved.

HR Match takes a CSV with `employee_id,email,employment_status`. It normalizes
email case and whitespace, flags unmatched accounts, marks duplicate emails
or employee IDs ambiguous, and flags unknown or empty employment statuses
for manual review. HR input is processed in memory.

## Reviews and exports

Open Reviews and enter a campaign name and reviewer label. Each campaign
captures one item per current account with its effective grants and paths.
Choose Approve, Reject, or Investigate and enter a reason. A campaign can be
closed once every item has a decision. JSON includes the captured evidence,
decisions, and audit events. CSV includes account outcomes and grant counts.

The server binds to loopback and accepts browser writes from its own origin.
The reviewer label is self-reported. The local database provides no independent
reviewer authentication or tamper-evident storage. Keep the service on a trusted
single-user machine. Review decisions record intent and do not revoke access.

## Reproducing QA checks

Run `pytest --cov=permission_map --cov-branch` from a Python 3.12 environment
with the project's dev dependencies. The HTTP tests require loopback sockets.

The browser smoke test requires Python Playwright, Chromium, and a local
axe-core JavaScript bundle. Run:

```sh
python scripts/check_governance_browser.py /tmp/permission-map-browser \
  --axe /path/to/axe.min.js --chromium /path/to/chromium
python scripts/benchmark_governance.py /tmp/permission-map-benchmark
```

Both scripts generate synthetic data. The browser run uses port 8765 and
saves screenshots, axe results, and a synthetic campaign report. The benchmark
measures single requests after each synthetic import and captures process peak
RSS. Its results depend on the host and are intended as comparison data.
