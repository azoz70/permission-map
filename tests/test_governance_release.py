"""HTTP, SQLite and import regression tests using synthetic records."""

import base64
import csv
import http.client
import json
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, StringIO
from threading import Thread

import pytest
from openpyxl import Workbook

from permission_map.database.db import get_database
from permission_map.web.app import MAX_UPLOAD_BYTES, Handler, ThreadingHTTPServer

HOST = "127.0.0.1:8765"
ORIGIN = "http://" + HOST
USER_CSV = (
    "user_id,name,email\n"
    "s-1,Synthetic One,s1@example.invalid\n"
    "s-2,Synthetic Two,s2@example.invalid\n"
    "svc,Synthetic Service,svc@example.invalid\n"
    "s-3,Synthetic Three,s3@example.invalid\n"
)


@pytest.fixture
def request_api(tmp_path, monkeypatch):
    monkeypatch.setenv("PERMISSION_MAP_DATA_DIR", str(tmp_path))
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()

        def request(path, body=None, headers=None):
            method = "GET" if body is None else "POST"
            fields = {"Host": HOST, "Origin": ORIGIN, "Content-Type": "application/json"}
            fields.update(headers or {})
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
            try:
                connection.request(method, path, None if body is None else json.dumps(body), fields)
                response = connection.getresponse()
                raw = response.read().decode()
                payload = (
                    json.loads(raw)
                    if response.headers.get_content_type() == ("application/json")
                    else raw
                )
                return response.status, payload, response.headers
            finally:
                connection.close()

        try:
            yield request
        finally:
            server.shutdown()
            thread.join()


def upload(api, entity, content, file_format="csv"):
    return api("/api/import", {"entity": entity, "content": content, "format": file_format})


def xlsx(*rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return base64.b64encode(output.getvalue()).decode()


@pytest.mark.parametrize(
    "content",
    [
        "user_id,name\ns-1,Name,Extra\n",
        "user_id,name\ns-1\n",
        "user_id,user_id\ns-1,s-2\n",
        'user_id,name\ns-1,"Unclosed\n',
        "user_id,name\ns-1,One\ns-1,Again\n",
    ],
)
def test_malformed_import_is_atomic(request_api, content):
    assert upload(request_api, "users", content)[0] == 422
    assert request_api("/api/summary")[1]["users"] == 0


def test_xlsx_import_and_validation(request_api):
    assert (
        upload(
            request_api, "users", xlsx(["user_id", "name"], ["s-1", "Synthetic"], ["s-2"]), "xlsx"
        )[1]["imported"]
        == 2
    )
    assert upload(request_api, "groups", xlsx(["group_id"], ["=1+1"]), "xlsx")[0] == 422
    assert upload(request_api, "users", "bm90IGEgd29ya2Jvb2s=", "xlsx")[0] == 422
    assert upload(request_api, "users", xlsx(["user_id"], ["s-3"], ["s-3"]), "xlsx")[0] == 422
    assert request_api("/api/summary")[1]["users"] == 2


def test_hr_access_and_duplicate_relationships(request_api):
    api = request_api
    fixtures = {
        "users": USER_CSV,
        "groups": "group_id,name\ng,Synthetic group\n",
        "roles": "role_id,name,is_admin\nr,Synthetic admin,true\n",
        "resources": "resource_id,name\nsystem,Synthetic system\n",
        "permissions": "permission_id,resource_id,action\np,system,write\n",
        "memberships": "user_id,group_id\ns-1,g\n",
        "role_assignments": "role_id,group_id\nr,g\n",
        "role_permissions": "role_id,permission_id\nr,p\n",
    }
    for entity, content in fixtures.items():
        assert upload(api, entity, content)[0] == 200
    for entity in ("memberships", "role_assignments", "role_permissions"):
        assert upload(api, entity, fixtures[entity])[1]["imported"] == 0
    assert upload(api, "memberships", "user_id,group_id\nmissing,g\n")[0] == 422
    users = {u["external_id"]: u for u in api("/api/access")[1]["users"]}
    assert users["s-1"]["privileged"]
    (grant,) = users["s-1"]["grants"]
    assert grant["path"] == ["user:s-1", "group:g", "role:r", "permission:p"]
    assert not grant["direct"]
    report = api(
        "/api/hr-reconcile",
        {
            "content": (
                "employee_id,email,employment_status\n"
                "EMP1,S1@example.invalid,terminated\n"
                "EMP2,s2@example.invalid,mystery\n"
                "EMP3,s3@example.invalid,active\n"
                "EMP3,other@example.invalid,active\n"
            )
        },
    )[1]
    outcomes = {a["user_id"]: a["status"] for a in report["accounts"]}
    assert outcomes == {"s-1": "leaver", "s-2": "invalid", "svc": "unmatched", "s-3": "ambiguous"}
    assert (
        api(
            "/api/hr-reconcile",
            {"content": ("employee_id,email,employment_status\nEMP1,s1@example.invalid\n")},
        )[0]
        == 422
    )


def test_campaign_audit_snapshot_and_export(request_api):
    api = request_api
    assert api("/api/campaigns", {"name": "Synthetic", "reviewer": "Reviewer"})[0] == 409
    assert upload(api, "users", "user_id,name\ns-1,Original\n")[0] == 200
    status, created, _ = api("/api/campaigns", {"name": "Synthetic", "reviewer": "Reviewer"})
    assert status == 201
    path = f"/api/campaigns/{created['id']}"
    assert api(path + "/close", {})[0] == 409
    assert upload(api, "users", "user_id,name\ns-1,Updated\n")[0] == 200
    (item,) = api(path)[1]["items"]
    assert item["evidence"]["name"] == "Original"
    item_path = f"{path}/items/{item['id']}"
    assert api(item_path, {"decision": "other", "reason": "Example"})[0] == 422
    assert api(item_path, {"decision": "investigate", "reason": "Example"})[0] == 200
    decision = {"decision": "approve", "reason": "=1+1"}
    assert api(item_path, decision)[0] == 200
    assert api(item_path, decision)[0] == 200
    assert api(path + "/close", {})[0] == 200
    assert api(item_path, {"decision": "reject", "reason": "Example"})[0] == 409
    report = api(path + "/report.json")[1]
    assert report["counts"]["approve"] == 1
    assert [event["kind"] for event in report["audit"]] == [
        "created",
        "decided",
        "decided",
        "closed",
    ]
    assert report["audit"][2]["previous_decision"] == "investigate"
    assert report["audit"][2]["actor"] == "Reviewer"
    with get_database().connection() as database:
        assert database.execute("SELECT decision FROM campaign_items").fetchone()[0] == "approve"
    _, data, headers = api(path + "/report.csv")
    assert headers["Content-Disposition"] == 'attachment; filename="campaign-1.csv"'
    (row,) = csv.DictReader(StringIO(data))
    assert row["reason"] == "'=1+1"


def test_defensive_http_boundary(request_api):
    api = request_api
    body = {"entity": "users", "content": USER_CSV}
    assert api("/", headers={"Host": "outside.example.invalid"})[0] == 403
    assert api("/api/import", body, {"Origin": "http://localhost:8765"})[0] == 403
    assert api("/api/import", body, {"Content-Type": "text/plain"})[0] == 415
    assert api("/api/import", [], {})[0] == 400
    assert api("/api/import", body, {"Content-Length": str(MAX_UPLOAD_BYTES + 1)})[0] == 413
    assert api("/api/import", {"entity": [], "content": ""})[0] == 422
    assert api("/api/summary")[1]["users"] == 0
    headers = api("/")[2]
    assert headers["X-Frame-Options"] == "DENY"
    assert "script-src 'sha256-" in headers["Content-Security-Policy"]
    assert headers["Cache-Control"] == "no-store"


def test_campaign_concurrent_decisions_record_consistent_history(request_api):
    api = request_api
    assert upload(api, "users", "user_id\ns-1\n")[0] == 200
    created = api("/api/campaigns", {"name": "Concurrent", "reviewer": "QA"})[1]
    path = f"/api/campaigns/{created['id']}"
    (item,) = api(path)[1]["items"]
    endpoint = f"{path}/items/{item['id']}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(
            pool.map(
                lambda decision: api(endpoint, {"decision": decision, "reason": decision})[0],
                ("approve", "reject"),
            )
        )
    assert statuses == [200, 200]
    report = api(path + "/report.json")[1]
    first, second = report["audit"][1:]
    assert second["previous_decision"] == first["decision"]
    assert report["items"][0]["decision"] == second["decision"]
