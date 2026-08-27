from datetime import datetime

import pytest

from app.api.application.services import (
    AlertService,
    MetricsService,
    ServerService,
    SystemService,
)
from app.api.domain.entities import Server, ServerAlert, ServerMetrics
from app.api.domain.enums import AlertSeverity, Environment, ServerStatus
from app.api.domain.exceptions import DuplicateServerError, ServerNotFoundError


class FakeServerRepository:
    def __init__(self, items=None):
        self.items = list(items or [])

    def find_all(self):
        return list(self.items)

    def find_by_id(self, server_id):
        return next((item for item in self.items if item.id == server_id), None)

    def find_by_name(self, name):
        return next((item for item in self.items if item.name == name), None)

    def find_by_ip(self, ip):
        return next((item for item in self.items if item.ip == ip), None)

    def search(self, query):
        query = query.lower()
        return [
            item
            for item in self.items
            if query in item.name.lower() or query in item.ip
        ]

    def save(self, server):
        server.id = len(self.items) + 1
        self.items.append(server)
        return server

    def update_status(self, server_id, status):
        server = self.find_by_id(server_id)
        if server is None:
            return False
        server.status = status
        return True

    def delete(self, server_id):
        before = len(self.items)
        self.items = [item for item in self.items if item.id != server_id]
        return len(self.items) != before


class FakeMetricsRepository:
    def __init__(self):
        self.items = []

    def save(self, metrics):
        metrics.id = len(self.items) + 1
        self.items.append(metrics)
        return metrics

    def find_latest(self, server_id):
        items = [item for item in self.items if item.server_id == server_id]
        return items[-1] if items else None

    def find_history(self, server_id, limit=10):
        items = [item for item in self.items if item.server_id == server_id]
        return list(reversed(items[-limit:]))


class FakeAlertRepository:
    def __init__(self):
        self.items = []

    def save(self, alert):
        alert.id = len(self.items) + 1
        if alert.created_at is None:
            alert.created_at = datetime(2026, 8, 21, 10)
        self.items.append(alert)
        return alert

    def find_active(self):
        return [item for item in self.items if not item.resolved]

    def resolve(self, alert_id):
        alert = next((item for item in self.items if item.id == alert_id), None)
        if alert is None:
            return False
        alert.resolved = True
        return True


def make_server(
    name="web-server-01",
    ip="192.168.1.10",
    *,
    server_id=None,
    status=ServerStatus.ONLINE,
):
    return Server(
        name=name,
        ip=ip,
        environment=Environment.PRODUCTION,
        status=status,
        cpu_cores=8,
        memory_gb=16,
        disk_gb=500,
        id=server_id,
    )


def test_server_service_create_lookup_and_search():
    repository = FakeServerRepository()
    service = ServerService(repository)

    server = service.create_server(make_server())

    assert server.id == 1
    assert service.get_server(1) is server
    assert service.find_by_identifier("web-server-01") is server
    assert service.find_by_identifier("192.168.1.10") is server
    assert service.search_servers("web") == [server]


def test_server_service_rejects_duplicate_and_missing_servers():
    repository = FakeServerRepository()
    service = ServerService(repository)
    service.create_server(make_server())

    with pytest.raises(DuplicateServerError):
        service.create_server(make_server())

    with pytest.raises(ServerNotFoundError):
        service.get_server(999)

    with pytest.raises(ServerNotFoundError):
        service.find_by_identifier("unknown")


def test_server_service_rejects_empty_search():
    service = ServerService(FakeServerRepository())

    with pytest.raises(ValueError):
        service.search_servers("   ")


def test_metrics_service_delegates_to_repository():
    repository = FakeMetricsRepository()
    service = MetricsService(repository)

    first = service.add(
        ServerMetrics(
            server_id=1,
            cpu_usage_percent=50,
            memory_usage_percent=40,
            disk_usage_percent=30,
            uptime_seconds=100,
        )
    )
    second = service.add(
        ServerMetrics(
            server_id=1,
            cpu_usage_percent=70,
            memory_usage_percent=50,
            disk_usage_percent=35,
            uptime_seconds=200,
        )
    )

    assert service.latest(1) is second
    assert service.history(1, 1) == [second]
    assert service.history(1, 10) == [second, first]
    assert service.latest(999) is None


def test_alert_service_creates_and_lists_active_alerts():
    servers = FakeServerRepository([make_server(server_id=1)])
    server_service = ServerService(servers)
    alerts = FakeAlertRepository()
    service = AlertService(alerts, server_service)

    alert = service.create(
        "web-server-01",
        AlertSeverity.CRITICAL,
        "CPU usage exceeded threshold",
    )

    assert alert.server_id == 1
    assert alert.severity is AlertSeverity.CRITICAL
    assert service.active()[0].server == "web-server-01"

    assert alert.id is not None
    assert service.resolve(alert.id) is True
    assert service.active() == []


def test_alert_service_rejects_unknown_server():
    service = AlertService(
        FakeAlertRepository(),
        ServerService(FakeServerRepository()),
    )

    with pytest.raises(ServerNotFoundError):
        service.create("unknown", AlertSeverity.WARNING, "Test")


def test_system_service_aggregates_server_and_alert_statistics():
    servers = FakeServerRepository([
        make_server(server_id=1),
        make_server(
            name="db-server-01",
            ip="192.168.1.20",
            server_id=2,
            status=ServerStatus.MAINTENANCE,
        ),
        make_server(
            name="api-server-01",
            ip="192.168.1.30",
            server_id=3,
            status=ServerStatus.OFFLINE,
        ),
    ])
    alerts = FakeAlertRepository()
    alerts.save(ServerAlert(1, AlertSeverity.CRITICAL, "Down"))
    alerts.save(ServerAlert(2, AlertSeverity.WARNING, "High CPU"))
    resolved = alerts.save(ServerAlert(3, AlertSeverity.INFO, "Maintenance"))
    resolved.resolved = True

    stats = SystemService(servers, alerts).stats()

    assert stats == {
        "total_servers": 3,
        "servers_by_status": {
            "online": 1,
            "offline": 1,
            "maintenance": 1,
        },
        "active_alerts": 2,
        "alerts_by_severity": {
            "critical": 1,
            "warning": 1,
            "info": 0,
        },
    }
