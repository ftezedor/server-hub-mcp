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
    assert servers.find_by_name("test-server").id == server.id
    assert servers.find_by_ip("10.0.0.1").id == server.id

    metric = metrics.save(
        ServerMetrics(
            server_id=server.id,
            cpu_usage_percent=50,
            memory_usage_percent=40,
            disk_usage_percent=30,
            uptime_seconds=100,
        )
    )
    assert metrics.find_latest(server.id).id == metric.id
    assert metrics.find_history(server.id, 10) == [metric]

    alert = alerts.save(
        ServerAlert(
            server_id=server.id,
            severity=AlertSeverity.WARNING,
            message="test",
        )
    )
    assert alerts.find_active()[0].id == alert.id
    assert alerts.resolve(alert.id) is True
    assert alerts.find_active() == []

    servers.delete(server.id)
    assert servers.find_by_id(server.id) is None
    assert metrics.find_history(server.id) == []
    assert alerts.find_active() == []

    session.close()
