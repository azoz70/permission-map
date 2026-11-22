"""Generate synthetic identities and time real loopback governance API operations."""

import argparse
import base64
import json
import os
import resource
import tempfile
from pathlib import Path
from threading import Thread
from time import perf_counter
from urllib.request import Request, urlopen

from openpyxl import Workbook

from permission_map.web.app import Handler, ThreadingHTTPServer

HOST = "127.0.0.1:8765"


def benchmark(folder, size):
    folder.mkdir()
    os.environ["PERMISSION_MAP_DATA_DIR"] = str(folder / "data")
    users = "user_id,name,email\n" + "".join(
        f"qa-{i},Synthetic {i},qa{i}@example.invalid\n" for i in range(size)
    )
    hr = "employee_id,email,employment_status\n" + "".join(
        f"EMP-{i},qa{i}@example.invalid,{'terminated' if i % 5 == 0 else 'active'}\n"
        for i in range(size)
    )
    (folder / "users.csv").write_text(users)
    (folder / "hr.csv").write_text(hr)
    timings = {}
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()

        def measure(label, path, body=None):
            payload = json.dumps(body).encode() if body is not None else None
            request = Request(
                f"http://127.0.0.1:{server.server_port}/api/" + path,
                data=payload,
                headers={
                    "Host": HOST,
                    "Origin": "http://" + HOST,
                    "Content-Type": "application/json",
                },
            )
            start = perf_counter()
            with urlopen(request, timeout=30) as response:
                result = response.read()
            timings[label + "_ms"] = round((perf_counter() - start) * 1000, 1)
            return result

        try:
            assert (
                json.loads(
                    measure(
                        "import",
                        "import",
                        {
                            "entity": "users",
                            "content": users,
                        },
                    )
                )["imported"]
                == size
            )
            workbook = Workbook(write_only=True)
            sheet = workbook.create_sheet()
            for row in users.splitlines():
                sheet.append(row.split(","))
            xlsx = folder / "users.xlsx"
            workbook.save(xlsx)
            assert (
                json.loads(
                    measure(
                        "xlsx_import",
                        "import",
                        {
                            "entity": "users",
                            "format": "xlsx",
                            "content": base64.b64encode(xlsx.read_bytes()).decode(),
                        },
                    )
                )["imported"]
                == size
            )
            fixtures = {
                "groups": "group_id,name\ng,Synthetic reviewers\n",
                "roles": "role_id,name,is_admin\nr,Synthetic admin,true\n",
                "resources": "resource_id,name\nres,Synthetic resource\n",
                "permissions": "permission_id,resource_id,action\np,res,write\n",
                "role_permissions": "role_id,permission_id\nr,p\n",
                "role_assignments": "role_id,group_id\nr,g\n",
                "memberships": "user_id,group_id\n"
                + "".join(f"qa-{i},g\n" for i in range(0, size, 10)),
            }
            for entity, content in fixtures.items():
                assert json.loads(
                    measure(
                        entity + "_seed",
                        "import",
                        {
                            "entity": entity,
                            "content": content,
                        },
                    )
                )["ok"]
            assert json.loads(measure("summary", "summary"))["users"] == size
            inventory = json.loads(measure("inventory", "access"))
            assert len(inventory["users"]) == size
            assert sum(user["privileged"] for user in inventory["users"]) == (size + 9) // 10
            assert all(
                not grant["direct"] for user in inventory["users"] for grant in user["grants"]
            )
            reconciled = json.loads(measure("hr", "hr-reconcile", {"content": hr}))
            assert reconciled["totals"]["leaver"] == (size + 4) // 5
            campaign = json.loads(
                measure("campaign_create", "campaigns", {"name": "Synthetic", "reviewer": "QA"})
            )
            path = f"campaigns/{campaign['id']}"
            page = json.loads(measure("campaign_page", path))
            assert page["counts"]["pending"] == size
            assert len(page["items"]) == min(size, 25)
            if size > 25:
                following = json.loads(measure("next_page", path + f"?after={page['next_after']}"))
                assert following["items"][0]["id"] > page["items"][-1]["id"]
            item = page["items"][0]["id"]
            measure("decision", f"{path}/items/{item}", {"decision": "approve", "reason": "QA"})
            raw = measure("json_report", path + "/report.json")
            assert len(json.loads(raw)["items"]) == size
            timings["json_report_bytes"] = len(raw)
            raw = measure("csv_report", path + "/report.csv")
            assert len(raw.splitlines()) == size + 1
            timings["csv_report_bytes"] = len(raw)
        finally:
            server.shutdown()
            thread.join()
    return {
        "accounts": size,
        **timings,
        "process_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output, prefix="run-") as temporary:
        results = []
        for size in (1, 100, 1000, 10000, 50000):
            result = benchmark(Path(temporary) / str(size), size)
            print(json.dumps(result), flush=True)
            results.append(result)
    (args.output / "performance.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
