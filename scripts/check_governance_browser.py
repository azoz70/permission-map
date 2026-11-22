"""Run the local governance smoke test and save screenshots and axe results."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from openpyxl import Workbook
from playwright.sync_api import expect, sync_playwright

URL = "http://127.0.0.1:8765"


def check(page, artifacts, axe):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    scans = {}

    def scan(name):
        page.screenshot(path=artifacts / f"{name}.png", full_page=True)
        page.evaluate(axe.read_text(encoding="utf-8"))
        scans[name] = page.evaluate("async () => await axe.run()")

    page.goto(URL)
    expect(page.get_by_text("Local database loaded.")).to_be_visible()
    scan("overview")
    page.get_by_role("button", name="Import", exact=True).click()
    page.get_by_label("Entity type").select_option("users")
    workbook = Workbook()
    workbook.active.append(["user_id", "name", "email"])
    workbook.active.append(["qa-1", "Synthetic Browser Account", "qa1@example.invalid"])
    path = artifacts / "synthetic-browser.xlsx"
    workbook.save(path)
    workbook.close()
    page.get_by_label("Access file").set_input_files(path)
    page.get_by_role("button", name="Validate & Import").click()
    expect(page.get_by_text("Imported 1 of 1 rows into users")).to_be_visible()
    scan("excel-import")

    page.get_by_role("button", name="HR Match").click()
    page.get_by_label("HR CSV").set_input_files(
        {
            "name": "synthetic-hr.csv",
            "mimeType": "text/csv",
            "buffer": b"employee_id,email,employment_status\nE1,qa1@example.invalid,terminated\n",
        }
    )
    page.get_by_role("button", name="Match accounts").click()
    expect(page.get_by_text("qa-1 | leaver", exact=False)).to_be_visible()
    scan("hr-match")

    page.get_by_role("button", name="Reviews").click()
    page.get_by_label("Campaign name").fill("Synthetic quarterly review")
    page.get_by_label("Reviewer").fill("Synthetic operator")
    page.get_by_role("button", name="Create campaign").click()
    expect(page.get_by_text("Campaign open.")).to_be_visible()
    page.get_by_label("Decision", exact=True).select_option("reject")
    page.get_by_label("Reason", exact=True).fill("Synthetic access is no longer required")
    page.get_by_label("Reason", exact=True).press("Tab")
    expect(page.get_by_role("button", name="Save decision")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.get_by_text("Decision saved.")).to_be_visible()
    scan("campaign")
    page.reload()
    page.get_by_role("button", name="Reviews").click()
    expect(page.get_by_label("Decision", exact=True)).to_have_value("reject")
    page.get_by_role("button", name="Close campaign").click()
    expect(page.get_by_text("Campaign closed.")).to_be_visible()
    with page.expect_download() as event:
        page.get_by_role("link", name="Download JSON and audit history").click()
    report = json.loads(event.value.path().read_text())
    assert [entry["kind"] for entry in report["audit"]] == ["created", "decided", "closed"]
    with page.expect_download() as event:
        page.get_by_role("link", name="Download CSV").click()
    assert "reject" in event.value.path().read_text()
    (artifacts / "synthetic-campaign-report.json").write_text(json.dumps(report, indent=2))

    page.get_by_role("button", name="Access", exact=True).click()
    expect(page.get_by_text("qa-1 | Synthetic Browser Account", exact=False)).to_be_visible()
    scan("access")
    page.get_by_role("button", name="How It Works").click()
    scan("guide")
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_role("button", name="Reviews").click()
    expect(page.get_by_text("Campaign closed.")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") == 390
    scan("mobile-campaign")
    (artifacts / "axe-results.json").write_text(json.dumps(scans, indent=2))
    findings = {name: [v["id"] for v in result["violations"]] for name, result in scans.items()}
    print("Axe violations:", findings, flush=True)
    assert not any(findings.values()), findings
    assert not errors, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("--axe", type=Path, required=True)
    parser.add_argument("--chromium", type=Path, required=True)
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="permission-map-browser-") as folder:
        with (args.artifacts / "browser-server.log").open("w") as server_log:
            server = subprocess.Popen(
                [sys.executable, "-m", "permission_map.web.app"],
                env={**os.environ, "PERMISSION_MAP_DATA_DIR": folder},
                stdout=server_log,
                stderr=server_log,
            )
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError("Web server exited")
                    try:
                        with urlopen(URL, timeout=1):
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Web server did not start")
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(executable_path=args.chromium)
                    print("Chromium", browser.version, flush=True)
                    check(
                        browser.new_page(viewport={"width": 1366, "height": 950}),
                        args.artifacts,
                        args.axe,
                    )
                    browser.close()
            finally:
                server.terminate()
                server.wait(timeout=10)
    print("PASS Excel import, HR match, review, persistence, audit, exports and accessibility")


if __name__ == "__main__":
    main()
