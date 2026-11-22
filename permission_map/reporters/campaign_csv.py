"""CSV export of account-level review outcomes."""

import csv
from io import StringIO


def _spreadsheet_text(value):
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))
    ):
        return "'" + value
    return value


def campaign_csv(report):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["campaign", "reviewer", "account", "decision", "reason", "privileged", "grants"]
    )
    campaign = report["campaign"]
    for item in report["items"]:
        evidence = item["evidence"]
        writer.writerow(
            map(
                _spreadsheet_text,
                (
                    campaign["name"],
                    campaign["reviewer"],
                    item["account"],
                    item["decision"] or "pending",
                    item["reason"],
                    evidence["privileged"],
                    len(evidence["grants"]),
                ),
            )
        )
    return output.getvalue().encode("utf-8")
