import random

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
        "name": "cache-server-01",
        "ip": "192.168.1.30",
        "environment": Environment.STAGING,
        "status": ServerStatus.ONLINE,
        "cpu_cores": 4,
        "memory_gb": 8,
        "disk_gb": 100,
    },
    {
        "name": "api-server-01",
        "ip": "192.168.1.40",
        "environment": Environment.DEVELOPMENT,
        "status": ServerStatus.MAINTENANCE,
        "cpu_cores": 4,
        "memory_gb": 8,
        "disk_gb": 200,
    },
]


ALERTS = [
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
        "server_name": "api-server-01",
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
    """Create example metrics for servers without metrics."""
    for name, server_id in server_ids.items():
        if repository.find_latest(server_id) is not None:
            print(f"  ⏭️ Metrics already exist for '{name}'")
            continue

        for _ in range(5):
            repository.save(
                ServerMetrics(
                    server_id=server_id,
                    cpu_usage_percent=round(
                        random.uniform(10, 90),
                        1,
                    ),
                    memory_usage_percent=round(
                        random.uniform(20, 85),
                        1,
                    ),
                    disk_usage_percent=round(
                        random.uniform(30, 80),
                        1,
                    ),
                    temperature_celsius=round(
                        random.uniform(35, 75),
                        1,
                    ),
                    uptime_seconds=random.randint(
                        3600,
                        86400 * 30,
                    ),
                )
            )

        print(f"  📊 Metrics added for '{name}'")


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
    """Populate the database with example data."""
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