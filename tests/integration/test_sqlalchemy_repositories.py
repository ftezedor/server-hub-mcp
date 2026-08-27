from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.domain.entities import Server, ServerAlert, ServerMetrics
from app.api.domain.enums import AlertSeverity, Environment, ServerStatus
from app.api.infrastructure.persistence.sqlalchemy.database import Base
from app.api.infrastructure.persistence.sqlalchemy.repositories import (
    SQLAlchemyAlertRepository,
    SQLAlchemyMetricsRepository,
    SQLAlchemyServerRepository,
)


def test_sqlalchemy_repositories_round_trip_and_cascade_cleanup():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()

    servers = SQLAlchemyServerRepository(session)
    metrics = SQLAlchemyMetricsRepository(session)
    alerts = SQLAlchemyAlertRepository(session)

    server = servers.save(
        Server(
            name="test-server",
            ip="10.0.0.1",
            environment=Environment.DEVELOPMENT,
            status=ServerStatus.ONLINE,
            cpu_cores=4,
            memory_gb=8,
            disk_gb=100,
        )
    )

    assert server.id is not None
    server_id = server.id

    server_by_name = servers.find_by_name("test-server")
    assert server_by_name is not None
    assert server_by_name.id == server_id

    server_by_ip = servers.find_by_ip("10.0.0.1")
    assert server_by_ip is not None
    assert server_by_ip.id == server_id

    metric = metrics.save(
        ServerMetrics(
            server_id=server_id,
            cpu_usage_percent=50,
            memory_usage_percent=40,
            disk_usage_percent=30,
            uptime_seconds=100,
        )
    )

    latest_metric = metrics.find_latest(server_id)
    assert latest_metric is not None
    assert latest_metric.id == metric.id

    assert metrics.find_history(server_id, 10) == [metric]

    alert = alerts.save(
        ServerAlert(
            server_id=server_id,
            severity=AlertSeverity.WARNING,
            message="test",
        )
    )

    active_alerts = alerts.find_active()
    assert active_alerts
    assert active_alerts[0].id == alert.id

    assert alert.id is not None
    alert_id = alert.id

    assert alerts.resolve(alert_id) is True
    assert alerts.find_active() == []

    servers.delete(server_id)

    assert servers.find_by_id(server_id) is None
    assert metrics.find_history(server_id) == []
    assert alerts.find_active() == []

    session.close()