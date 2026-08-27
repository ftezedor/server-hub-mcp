"""
Black-box REST API tests.

These tests intentionally call the running Server Hub REST API over HTTP.
They do not import FastAPI's TestClient and do not call application services
directly.

Configuration:
    SERVER_HUB_API_URL=http://localhost:8080

Run:
    pytest -q tests/test_api.py
"""

import os
import uuid

import httpx
import pytest


BASE_URL = os.getenv("SERVER_HUB_API_URL", "http://localhost:8080").rstrip("/")
TIMEOUT = float(os.getenv("SERVER_HUB_API_TIMEOUT", "10"))


@pytest.fixture(scope="session")
def api():
    client = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)
    try:
        response = client.get("/")
        response.raise_for_status()
    except (httpx.HTTPError, AssertionError) as exc:
        client.close()
        pytest.fail(
            f"Server Hub REST API is not reachable at {BASE_URL}: {exc}"
        )
    yield client
    client.close()


def assert_json(response: httpx.Response, status_code: int):
    assert response.status_code == status_code, (
        f"{response.request.method} {response.request.url} returned "
        f"{response.status_code}: {response.text}"
    )
    return response.json()


def test_root(api):
    data = assert_json(api.get("/"), 200)

    assert data["message"] == "Server Hub API"
    assert data["status"] == "running"
    assert "version" in data
    assert data["docs"] == "/docs"


def test_health(api):
    data = assert_json(api.get("/health"), 200)

    assert data == {
        "status": "healthy",
    }


def test_readiness(api):
    data = assert_json(api.get("/ready"), 200)

    assert data == {
        "status": "ready",
    }


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_metadata(api, path):
    response = api.get(path)
    assert response.status_code == 200


def test_list_servers(api):
    data = assert_json(api.get("/api/servers"), 200)

    assert isinstance(data["servers"], list)
    assert data["total"] == len(data["servers"])

    if data["servers"]:
        server = data["servers"][0]
        assert {"id", "name", "ip", "environment", "status"} <= server.keys()


def test_get_existing_server(api):
    data = assert_json(api.get("/api/servers/1"), 200)

    assert data["id"] == 1
    assert data["name"]
    assert data["ip"]
    assert data["environment"]
    assert data["status"]


def test_get_unknown_server(api):
    response = api.get("/api/servers/999999")
    assert response.status_code == 404


def test_search_servers(api):
    data = assert_json(api.get("/api/search", params={"q": "web"}), 200)

    assert data["query"] == "web"
    assert isinstance(data["results"], list)
    assert data["count"] == len(data["results"])


def test_search_requires_query(api):
    response = api.get("/api/search", params={"q": ""})
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [1, 10, 50])
def test_get_metrics(api, limit):
    data = assert_json(
        api.get("/api/servers/1/metrics", params={"limit": limit}), 200
    )

    assert data["server"]["id"] == 1
    assert isinstance(data["metrics"], list)
    assert data["count"] == len(data["metrics"])
    assert len(data["metrics"]) <= limit


@pytest.mark.parametrize("limit", [0, 51, 999])
def test_metrics_limit_validation(api, limit):
    response = api.get(
        "/api/servers/1/metrics",
        params={"limit": limit},
    )
    assert response.status_code == 422


def test_metrics_unknown_server(api):
    response = api.get("/api/servers/999999/metrics")
    assert response.status_code == 404


def test_add_metrics(api):
    payload = {
        "cpu_usage_percent": 42.5,
        "memory_usage_percent": 55.0,
        "disk_usage_percent": 61.0,
        "temperature_celsius": 65.0,
        "uptime_seconds": 1932000,
    }

    data = assert_json(
        api.post("/api/servers/1/metrics", json=payload), 201
    )

    assert data["id"]
    assert "message" in data


def test_list_active_alerts(api):
    data = assert_json(api.get("/api/alerts"), 200)

    assert isinstance(data["alerts"], list)
    assert data["total"] == len(data["alerts"])


def test_create_alert_and_verify_it(api):
    message = f"REST API integration test {uuid.uuid4()}"

    data = assert_json(
        api.post(
            "/api/alerts",
            json={
                "server": "web-server-01",
                "severity": "warning",
                "message": message,
            },
        ),
        201,
    )

    assert data["id"]
    assert "message" in data

    alerts = assert_json(api.get("/api/alerts"), 200)
    assert any(alert.get("message") == message for alert in alerts["alerts"])


def test_create_alert_unknown_server(api):
    response = api.post(
        "/api/alerts",
        json={
            "server": "does-not-exist",
            "severity": "warning",
            "message": "Should fail",
        },
    )
    assert response.status_code == 404


def test_create_alert_invalid_severity(api):
    response = api.post(
        "/api/alerts",
        json={
            "server": "web-server-01",
            "severity": "invalid",
            "message": "Should fail",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"severity": "warning", "message": "missing server"},
        {"server": "web-server-01", "message": "missing severity"},
        {"server": "web-server-01", "severity": "warning"},
    ],
)
def test_create_alert_required_fields(api, payload):
    response = api.post("/api/alerts", json=payload)
    assert response.status_code == 422


def test_system_stats(api):
    data = assert_json(api.get("/api/stats"), 200)

    assert isinstance(data["total_servers"], int)
    assert isinstance(data["servers_by_status"], dict)
    assert isinstance(data["active_alerts"], int)
    assert isinstance(data["alerts_by_severity"], dict)
