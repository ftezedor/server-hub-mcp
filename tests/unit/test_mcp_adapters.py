from datetime import datetime

import httpx
import pytest

from app.api.domain.entities import Server, ServerAlert, ServerMetrics
from app.api.domain.enums import AlertSeverity, Environment, ServerStatus
from app.mcp.adapters.application import AppServerHubClient
from app.mcp.adapters.rest import RestServerHubClient


class FakeServerService:
    def __init__(self):
        self.server = Server(
            name="web-server-01",
            ip="192.168.1.10",
            environment=Environment.PRODUCTION,
            status=ServerStatus.ONLINE,
            cpu_cores=8,
            memory_gb=16,
            disk_gb=500,
            id=1,
            created_at=datetime(2026, 8, 21),
        )

    def search_servers(self, query):
        return [self.server] if query.lower() in self.server.name.lower() else []

    def get_server(self, server_id):
        if server_id != self.server.id:
            raise ValueError("not found")
        return self.server

    def find_by_identifier(self, identifier):
        if identifier in (self.server.name, self.server.ip):
            return self.server
        raise ValueError("not found")

    def find_by_id(self, server_id):
        return self.server if server_id == self.server.id else None


class FakeMetricsService:
    def __init__(self):
        self.metric = ServerMetrics(
            server_id=1,
            cpu_usage_percent=82.4,
            memory_usage_percent=71.2,
            disk_usage_percent=60.0,
            uptime_seconds=100,
            temperature_celsius=42.0,
            timestamp=datetime(2026, 8, 21, 8),
        )

    def latest(self, server_id):
        return self.metric if server_id == 1 else None

    def history(self, server_id, limit=10):
        return [self.metric][:limit]


class FakeAlertService:
    def active(self):
        return [
            type(
                "AlertView",
                (),
                {
                    "id": 7,
                    "server": "web-server-01",
                    "server_ip": "192.168.1.10",
                    "severity": AlertSeverity.WARNING,
                    "message": "High CPU",
                    "resolved": False,
                    "created_at": datetime(2026, 8, 21, 8),
                    "resolved_at": None,
                },
            )()
        ]

    def create(self, server, severity, message):
        return ServerAlert(
            server_id=1,
            severity=severity,
            message=message,
            id=8,
            created_at=datetime(2026, 8, 21, 9),
        )


class FakeSystemService:
    def stats(self):
        return {
            "total_servers": 1,
            "servers_by_status": {
                "online": 1,
                "offline": 0,
                "maintenance": 0,
            },
            "active_alerts": 1,
            "alerts_by_severity": {
                "critical": 0,
                "warning": 1,
                "info": 0,
            },
        }


class FakeServices:
    def __call__(self):
        yield {
            "servers": FakeServerService(),
            "metrics": FakeMetricsService(),
            "alerts": FakeAlertService(),
            "system": FakeSystemService(),
        }


def test_application_adapter_exposes_backend_contract(monkeypatch):
    monkeypatch.setattr("app.mcp.adapters.application.services", FakeServices())
    client = AppServerHubClient()

    search = client.search("web")
    server = client.get_server_by_id(1)
    metrics = client.get_metrics(1, 5)
    alerts = client.get_alerts()
    stats = client.get_stats()
    created = client.create_alert("web-server-01", "critical", "Test")

    assert search["count"] == 1
    assert search["results"][0]["name"] == "web-server-01"
    assert server["metrics"]["cpu_usage_percent"] == 82.4
    assert metrics["count"] == 1
    assert alerts["total"] == 1
    assert alerts["alerts"][0]["server"] == "web-server-01"
    assert stats["active_alerts"] == 1
    assert created["id"] == 8


def test_rest_adapter_builds_expected_request(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": 10, "message": "created"}

        text = ""
        reason_phrase = "OK"

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    client = RestServerHubClient("http://localhost:8080/api", timeout=3)
    result = client.create_alert("web-server-01", "warning", "High CPU")

    assert result["id"] == 10
    assert captured == {
        "method": "POST",
        "url": "http://localhost:8080/api/alerts",
        "kwargs": {
            "timeout": 3,
            "json": {
                "server": "web-server-01",
                "severity": "warning",
                "message": "High CPU",
            },
        },
    }


def test_rest_adapter_translates_http_errors(monkeypatch):
    request = httpx.Request("GET", "http://localhost:8080/api/stats")
    response = httpx.Response(
        404,
        request=request,
        json={"detail": "Server not found"},
    )

    def fake_request(*args, **kwargs):
        return response

    monkeypatch.setattr(httpx, "request", fake_request)

    client = RestServerHubClient("http://localhost:8080/api")

    with pytest.raises(RuntimeError, match="404.*Server not found"):
        client.get_stats()


def test_rest_adapter_translates_connection_errors(monkeypatch):
    def fake_request(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "request", fake_request)

    client = RestServerHubClient("http://localhost:8080/api")

    with pytest.raises(RuntimeError, match="Unable to reach Server Hub API"):
        client.get_stats()
