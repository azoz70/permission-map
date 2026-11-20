# Architecture

PERMISSION MAP is built as a layered, modular application. Analysis rules are
never coupled to the CLI: the command layer only orchestrates and renders, while
the engines hold the logic.

## Layers

```
┌─────────────────────────────────────────────────────────┐
│ CLI Layer                cli/commands.py, cli/dashboard │
├─────────────────────────────────────────────────────────┤
│ Input & Import Layer     importers/{csv,json,excel}     │
├─────────────────────────────────────────────────────────┤
│ Normalization Layer      core/normalizer.py             │
├─────────────────────────────────────────────────────────┤
│ Graph Engine             core/graph_engine.py           │
├─────────────────────────────────────────────────────────┤
│ Analysis Engines         analyzers/{permission_analyzer, │
│                          risk_engine, change_detector}  │
├─────────────────────────────────────────────────────────┤
│ Review Engine            reviewers/access_review.py      │
├─────────────────────────────────────────────────────────┤
│ Reporting Engine         reporters/{html,csv,json}       │
├─────────────────────────────────────────────────────────┤
│ Database Layer           database/db.py, repositories   │
└─────────────────────────────────────────────────────────┘
```

## Responsibilities

- **CLI Layer** — Typer commands, Rich rendering, dashboard and logos.
- **Input & Import Layer** — reads CSV/JSON/Excel files into raw records.
- **Normalization Layer** — maps source-specific columns to the unified model and
  validates the data.
- **Graph Engine** — builds a `networkx` graph of users → groups → roles →
  permissions → resources for relationship queries.
- **Analysis Engines** — produce structured findings (privilege, risk, change).
- **Review Engine** — records access-review decisions with an audit trail.
- **Reporting Engine** — emits HTML/CSV/JSON/summary reports.
- **Database Layer** — SQLite schema, persistence and repositories.

## Data flow

```
source files → importers → normalizer → database
                                        │
                     graph engine ←─────┤
                        │
              ┌─────────┼──────────┐
              ▼         ▼          ▼
        risk engine  change detector  review engine
              │         │              │
              └────┬────┘              │
                   ▼                   ▼
               findings            access_reviews
                   │                   │
                   └───────┬───────────┘
                           ▼
                     reports (HTML/CSV/JSON)
```

## Design principles

- **Local-first** — no network access, no telemetry, no cloud.
- **Read-only** — imported files are never executed and external IAM systems are
  never modified.
- **Honest results** — the UI only ever displays data read from the database;
  empty state is shown as empty, never as fabricated sample numbers.
