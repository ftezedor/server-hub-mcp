from app.api.application.services import AlertService, MetricsService, ServerService, SystemService
from app.api.infrastructure.persistence.sqlalchemy import (
    SQLAlchemyAlertRepository,
    SQLAlchemyMetricsRepository,
    SQLAlchemyServerRepository,
    get_session,
)


def services():
    session = get_session()
    try:
        servers = SQLAlchemyServerRepository(session)
        metrics = SQLAlchemyMetricsRepository(session)
        alerts = SQLAlchemyAlertRepository(session)
        
        server_service = ServerService(servers)
        alert_service = AlertService(alerts, server_service)

        yield {
            "servers": server_service,
            "metrics": MetricsService(metrics),
            "alerts": alert_service,
            "system": SystemService(servers, alerts),
        }
    finally:
        session.close()
