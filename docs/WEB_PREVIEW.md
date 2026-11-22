# Local web preview (development)

Run from the repository root after installing the project:

```bash
python -m permission_map.web.app
```

Open http://127.0.0.1:8765.

This is the first **read-only** web integration. It reads the existing graph summary from a local SQLite database and includes the approved green/dark design and a How It Works section. It does **not** yet implement Excel/CSV upload, HR matching, review campaigns, reporting, or authentication.

Security boundaries: binds to loopback only, rejects POST, no remote scripts or CDN dependencies. Do not expose it via reverse proxy or public network. The database filename must be verified against the current CLI before production use.

Implementation milestones: verify database path and graph schema; add import preview with validation; build identity reconciliation; implement review campaign state machine and audit trail; test report exports and package for release.
