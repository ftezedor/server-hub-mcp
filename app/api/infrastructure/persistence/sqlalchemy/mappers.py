from app.api.domain.entities import Server, ServerAlert, ServerMetrics
from app.api.domain.enums import AlertSeverity, Environment, ServerStatus
from .models import AlertModel, MetricsModel, ServerModel


def to_server(model: ServerModel) -> Server:
    return Server(
        id=model.id,
        name=model.name,
        ip=model.ip,
        environment=Environment(model.environment),
        status=ServerStatus(model.status),
        cpu_cores=model.cpu_cores,
        memory_gb=model.memory_gb,
        disk_gb=model.disk_gb,
        last_updated=model.last_updated,
        created_at=model.created_at,
    )


def to_metrics(model: MetricsModel) -> ServerMetrics:
    return ServerMetrics(
        id=model.id,
        server_id=model.server_id,
        cpu_usage_percent=model.cpu_usage_percent,
        memory_usage_percent=model.memory_usage_percent,
        disk_usage_percent=model.disk_usage_percent,
        temperature_celsius=model.temperature_celsius,
        uptime_seconds=model.uptime_seconds,
        timestamp=model.timestamp,
    )


def to_alert(model: AlertModel) -> ServerAlert:
    return ServerAlert(
        id=model.id,
        server_id=model.server_id,
        severity=AlertSeverity(model.severity),
        message=model.message,
        resolved=model.resolved,
        created_at=model.created_at,
        resolved_at=model.resolved_at,
    )
