from datetime import datetime, timedelta, timezone

from app.api.domain.entities.alert import ServerAlert
from app.api.domain.entities.metrics import ServerMetrics
from app.api.domain.entities.server import Server
from app.api.domain.enums import AlertSeverity, Environment, ServerStatus
from app.api.infrastructure.persistence.sqlalchemy.database import (
    get_session,
    init_database,
)
from app.api.infrastructure.persistence.sqlalchemy.repositories import (
    SQLAlchemyAlertRepository,
    SQLAlchemyMetricsRepository,
    SQLAlchemyServerRepository,
)


# The seed data is intentionally deterministic. It is designed to provide
# meaningful scenarios for the MCP Playground rather than random values.
SERVERS = [
    {
        "name": "web-server-01",
        "ip": "192.168.1.10",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 8,
        "memory_gb": 16,
        "disk_gb": 500,
    },
    {
        "name": "web-server-02",
        "ip": "192.168.1.11",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.OFFLINE,
        "cpu_cores": 8,
        "memory_gb": 16,
        "disk_gb": 500,
    },
    {
        "name": "web-server-03",
        "ip": "192.168.1.12",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 8,
        "memory_gb": 16,
        "disk_gb": 500,
    },
    {
        "name": "db-server-01",
        "ip": "192.168.1.20",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 16,
        "memory_gb": 64,
        "disk_gb": 2000,
    },
    {
        "name": "db-server-02",
        "ip": "192.168.1.21",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 16,
        "memory_gb": 64,
        "disk_gb": 2000,
    },
    {
        "name": "api-server-01",
        "ip": "192.168.1.40",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 8,
        "memory_gb": 16,
        "disk_gb": 300,
    },
    {
        "name": "api-server-02",
        "ip": "192.168.1.41",
        "environment": Environment.PRODUCTION,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 8,
        "memory_gb": 32,
        "disk_gb": 300,
    },
    {
        "name": "cache-server-01",
        "ip": "192.168.1.30",
        "environment": Environment.STAGING,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 4,
        "memory_gb": 8,
        "disk_gb": 100,
    },
    {
        "name": "batch-server-01",
        "ip": "192.168.1.50",
        "environment": Environment.STAGING,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 8,
        "memory_gb": 32,
        "disk_gb": 500,
    },
    {
        "name": "api-server-dev",
        "ip": "192.168.1.60",
        "environment": Environment.DEVELOPMENT,
        "status": ServerStatus.MAINTENANCE,
        "cpu_cores": 4,
        "memory_gb": 8,
        "disk_gb": 200,
    },
]


# Each list contains the 10 most recent samples, ordered oldest -> newest.
# The scenarios deliberately include stable, degrading, and high-utilization
# servers so an LLM has something meaningful to compare and correlate.
METRICS = {
    "web-server-01": {
        "cpu": [35.0, 37.0, 39.0, 41.0, 42.0, 44.0, 46.0, 47.0, 49.0, 51.0],
        "memory": [45.0, 45.5, 46.0, 46.5, 47.0, 47.5, 48.0, 48.5, 49.0, 50.0],
        "disk": [52.0, 52.0, 53.0, 53.0, 54.0, 54.0, 55.0, 55.0, 56.0, 56.0],
        "temperature": [43.0, 43.2, 43.5, 43.8, 44.0, 44.2, 44.5, 44.8, 45.0, 45.2],
        "uptime": 604800,
    },
    "web-server-02": {
        "cpu": [72.0, 70.0, 68.0, 65.0, 63.0, 61.0, 59.0, 57.0, 55.0, 53.0],
        "memory": [66.0, 65.0, 64.0, 63.0, 62.0, 61.0, 60.0, 59.0, 58.0, 57.0],
        "disk": [70.0, 70.0, 71.0, 71.0, 72.0, 72.0, 73.0, 73.0, 74.0, 74.0],
        "temperature": [51.0, 50.5, 50.0, 49.5, 49.0, 48.5, 48.0, 47.5, 47.0, 46.5],
        "uptime": 432000,
    },
    "web-server-03": {
        "cpu": [41.0, 43.0, 44.0, 46.0, 45.0, 47.0, 48.0, 49.0, 50.0, 52.0],
        "memory": [51.0, 52.0, 52.0, 53.0, 54.0, 54.0, 55.0, 56.0, 56.0, 57.0],
        "disk": [48.0, 48.0, 49.0, 49.0, 50.0, 50.0, 51.0, 51.0, 52.0, 52.0],
        "temperature": [44.0, 44.2, 44.5, 44.7, 45.0, 45.2, 45.5, 45.8, 46.0, 46.3],
        "uptime": 518400,
    },
    "db-server-01": {
        "cpu": [61.0, 68.0, 72.0, 76.0, 80.0, 84.0, 87.0, 90.0, 92.0, 94.2],
        "memory": [68.0, 69.0, 70.0, 71.0, 72.0, 73.0, 74.0, 75.0, 76.0, 77.0],
        "disk": [61.0, 62.0, 63.0, 64.0, 65.0, 66.0, 67.0, 68.0, 69.0, 70.0],
        "temperature": [54.0, 55.0, 56.0, 57.0, 58.0, 59.0, 60.0, 61.0, 62.0, 63.0],
        "uptime": 1296000,
    },
    "db-server-02": {
        "cpu": [38.0, 39.0, 40.0, 41.0, 39.0, 40.0, 41.0, 42.0, 40.0, 41.0],
        "memory": [58.0, 58.0, 59.0, 59.0, 60.0, 60.0, 59.0, 60.0, 61.0, 60.0],
        "disk": [46.0, 46.0, 47.0, 47.0, 48.0, 48.0, 49.0, 49.0, 50.0, 50.0],
        "temperature": [42.0, 42.5, 43.0, 42.5, 43.0, 43.5, 43.0, 43.5, 44.0, 43.5],
        "uptime": 2592000,
    },
    "api-server-01": {
        "cpu": [48.0, 50.0, 52.0, 54.0, 56.0, 58.0, 60.0, 61.0, 63.0, 65.0],
        "memory": [57.0, 58.0, 59.0, 60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0],
        "disk": [43.0, 44.0, 44.0, 45.0, 45.0, 46.0, 46.0, 47.0, 47.0, 48.0],
        "temperature": [46.0, 46.2, 46.5, 46.7, 47.0, 47.2, 47.5, 47.7, 48.0, 48.2],
        "uptime": 777600,
    },
    "api-server-02": {
        "cpu": [55.0, 59.0, 63.0, 67.0, 71.0, 74.0, 77.0, 80.0, 82.0, 84.0],
        "memory": [62.0, 66.0, 70.0, 74.0, 78.0, 81.0, 84.0, 87.0, 89.0, 91.3],
        "disk": [50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0],
        "temperature": [49.0, 49.5, 50.0, 50.5, 51.0, 51.5, 52.0, 52.5, 53.0, 53.5],
        "uptime": 950400,
    },
    "cache-server-01": {
        "cpu": [36.0, 37.0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0],
        "memory": [72.0, 73.0, 74.0, 75.0, 76.0, 77.0, 78.0, 79.0, 80.0, 81.0],
        "disk": [62.0, 62.0, 63.0, 63.0, 64.0, 64.0, 65.0, 65.0, 66.0, 66.0],
        "temperature": [64.0, 66.0, 68.0, 70.0, 72.0, 74.0, 75.0, 77.0, 79.0, 81.5],
        "uptime": 345600,
    },
    "batch-server-01": {
        "cpu": [22.0, 24.0, 26.0, 35.0, 48.0, 63.0, 71.0, 52.0, 34.0, 27.0],
        "memory": [41.0, 42.0, 43.0, 50.0, 59.0, 68.0, 72.0, 61.0, 49.0, 44.0],
        "disk": [55.0, 55.0, 56.0, 56.0, 57.0, 58.0, 58.0, 59.0, 59.0, 60.0],
        "temperature": [40.0, 41.0, 42.0, 45.0, 49.0, 53.0, 56.0, 50.0, 45.0, 42.0],
        "uptime": 172800,
    },
    "api-server-dev": {
        "cpu": [18.0, 21.0, 19.0, 24.0, 22.0, 20.0, 23.0, 21.0, 19.0, 22.0],
        "memory": [35.0, 36.0, 35.0, 37.0, 36.0, 35.0, 38.0, 37.0, 36.0, 35.0],
        "disk": [31.0, 32.0, 32.0, 33.0, 33.0, 34.0, 34.0, 35.0, 35.0, 36.0],
        "temperature": [37.0, 37.5, 38.0, 38.5, 39.0, 39.5, 40.0, 40.5, 41.0, 41.5],
        "uptime": 86400,
    },
}


ALERTS = [
    {
        "server_name": "db-server-01",
        "severity": AlertSeverity.CRITICAL,
        "message": "Database connection pool exhausted",
    },
    {
        "server_name": "db-server-01",
        "severity": AlertSeverity.WARNING,
        "message": "CPU usage above 80% for 5 minutes",
    },
    {
        "server_name": "web-server-02",
        "severity": AlertSeverity.CRITICAL,
        "message": "Server unreachable - connection timeout",
    },
    {
        "server_name": "api-server-02",
        "severity": AlertSeverity.CRITICAL,
        "message": "API response latency above threshold",
    },
    {
        "server_name": "api-server-02",
        "severity": AlertSeverity.WARNING,
        "message": "Memory usage above 85%",
    },
    {
        "server_name": "cache-server-01",
        "severity": AlertSeverity.WARNING,
        "message": "Temperature above recommended operating range",
    },
    {
        "server_name": "api-server-01",
        "severity": AlertSeverity.WARNING,
        "message": "CPU utilization trending upward",
    },
    {
        "server_name": "batch-server-01",
        "severity": AlertSeverity.INFO,
        "message": "Batch workload completed successfully",
    },
    {
        "server_name": "api-server-dev",
        "severity": AlertSeverity.INFO,
        "message": "Scheduled maintenance for version upgrade",
    },
]


def seed_servers(repository: SQLAlchemyServerRepository) -> dict[str, int]:
    """Create example servers and return their IDs."""
    server_ids: dict[str, int] = {}

    for data in SERVERS:
        existing = repository.find_by_name(data["name"])

        if existing is not None:
            if existing.id is None:
                raise RuntimeError(
                    f"Persisted server '{existing.name}' has no ID"
                )

            server_ids[existing.name] = existing.id
            print(
                f"  ⏭️ Server '{existing.name}' already exists "
                f"(ID: {existing.id})"
            )
            continue

        server = repository.save(Server(**data))

        if server.id is None:
            raise RuntimeError(
                f"Created server '{server.name}' has no ID"
            )

        server_ids[server.name] = server.id

        print(
            f"  ✅ Server '{server.name}' created "
            f"(ID: {server.id})"
        )
    return server_ids


def seed_metrics(
    repository: SQLAlchemyMetricsRepository,
    server_ids: dict[str, int],
) -> None:
    """Create deterministic metric history for servers without metrics."""
    sample_count = 10
    now = datetime.now(timezone.utc)

    for name, server_id in server_ids.items():
        if repository.find_latest(server_id) is not None:
            print(f"  ⏭️ Metrics already exist for '{name}'")
            continue

        data = METRICS[name]

        for index in range(sample_count):
            repository.save(
                ServerMetrics(
                    server_id=server_id,
                    cpu_usage_percent=data["cpu"][index],
                    memory_usage_percent=data["memory"][index],
                    disk_usage_percent=data["disk"][index],
                    temperature_celsius=data["temperature"][index],
                    uptime_seconds=data["uptime"] + (index * 300),
                    timestamp=now - timedelta(minutes=(sample_count - 1 - index) * 5),
                )
            )

        print(f"  📊 {sample_count} deterministic metrics added for '{name}'")


def seed_alerts(
    repository: SQLAlchemyAlertRepository,
    server_ids: dict[str, int],
) -> None:
    """Create example alerts without duplicating active alerts."""
    existing_alerts = repository.find_active()

    for alert_data in ALERTS:
        server_id = server_ids.get(alert_data["server_name"])

        if server_id is None:
            continue

        duplicate = any(
            alert.server_id == server_id
            and alert.message == alert_data["message"]
            for alert in existing_alerts
        )

        if duplicate:
            print(
                f"  ⏭️ Alert already exists: "
                f"{alert_data['message']}"
            )
            continue

        repository.save(
            ServerAlert(
                server_id=server_id,
                severity=alert_data["severity"],
                message=alert_data["message"],
            )
        )

        print(
            f"  ⚠️ Alert created: "
            f"{alert_data['message']}"
        )


def seed_database() -> None:
    """Populate the database with deterministic example data."""
    print("🌱 Initializing database with example data...")

    session = get_session()
    try:
        server_repository = SQLAlchemyServerRepository(session)
        metrics_repository = SQLAlchemyMetricsRepository(session)
        alert_repository = SQLAlchemyAlertRepository(session)

        server_ids = seed_servers(server_repository)
        seed_metrics(metrics_repository, server_ids)
        seed_alerts(alert_repository, server_ids)

        print("✅ Database populated successfully!")
    finally:
        session.close()


if __name__ == "__main__":
    init_database()
    seed_database()
