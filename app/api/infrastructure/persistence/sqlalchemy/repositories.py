from datetime import datetime, timezone
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session
from app.api.domain.entities import Server, ServerAlert, ServerMetrics
from app.api.domain.enums import ServerStatus
from .mappers import to_alert, to_metrics, to_server
from .models import AlertModel, MetricsModel, ServerModel
from typing import Any, cast
from sqlalchemy.engine import CursorResult

class SQLAlchemyServerRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_by_id(self, server_id: int) -> Server | None:
        model = self.session.get(ServerModel, server_id)
        return to_server(model) if model else None

    def find_by_name(self, name: str) -> Server | None:
        model = self.session.scalar(select(ServerModel).where(ServerModel.name == name))
        return to_server(model) if model else None

    def find_by_ip(self, ip: str) -> Server | None:
        model = self.session.scalar(select(ServerModel).where(ServerModel.ip == ip))
        return to_server(model) if model else None

    def search(self, query: str) -> list[Server]:
        pattern = f"%{query}%"
        stmt = select(ServerModel).where(
            (ServerModel.name.ilike(pattern)) | ServerModel.ip.ilike(pattern)
        ).order_by(ServerModel.name)
        return [to_server(m) for m in self.session.scalars(stmt)]

    def find_all(self) -> list[Server]:
        return [to_server(m) for m in self.session.scalars(select(ServerModel).order_by(ServerModel.name))]

    def save(self, server: Server) -> Server:
        model = ServerModel(
            name=server.name,
            ip=server.ip,
            environment=server.environment.value,
            status=server.status.value,
            cpu_cores=server.cpu_cores,
            memory_gb=server.memory_gb,
            disk_gb=server.disk_gb,
            last_updated=server.last_updated,
            created_at=server.created_at,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return to_server(model)

    def update_status(self, server_id: int, status: ServerStatus) -> bool:
        
        result = cast(
            CursorResult[Any],
            self.session.execute(
                update(ServerModel)
                .where(ServerModel.id == server_id)
                .values(
                    status=status.value,
                    last_updated=datetime.now(timezone.utc),
                )
            ),
        )
        self.session.commit()
        return result.rowcount == 1

    def delete(self, server_id: int) -> bool:
        self.session.execute(delete(MetricsModel).where(MetricsModel.server_id == server_id))
        self.session.execute(delete(AlertModel).where(AlertModel.server_id == server_id))
        result = cast(
            CursorResult[Any],
            self.session.execute(
                delete(ServerModel).where(ServerModel.id == server_id)
            ),
        )
        self.session.commit()
        return result.rowcount == 1


class SQLAlchemyMetricsRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, metrics: ServerMetrics) -> ServerMetrics:
        model = MetricsModel(
            server_id=metrics.server_id,
            cpu_usage_percent=metrics.cpu_usage_percent,
            memory_usage_percent=metrics.memory_usage_percent,
            disk_usage_percent=metrics.disk_usage_percent,
            temperature_celsius=metrics.temperature_celsius,
            uptime_seconds=metrics.uptime_seconds,
            timestamp=metrics.timestamp,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return to_metrics(model)

    def find_latest(self, server_id: int) -> ServerMetrics | None:
        stmt = select(MetricsModel).where(MetricsModel.server_id == server_id).order_by(MetricsModel.timestamp.desc()).limit(1)
        model = self.session.scalar(stmt)
        return to_metrics(model) if model else None

    def find_history(self, server_id: int, limit: int = 10) -> list[ServerMetrics]:
        stmt = select(MetricsModel).where(MetricsModel.server_id == server_id).order_by(MetricsModel.timestamp.desc()).limit(limit)
        return [to_metrics(m) for m in self.session.scalars(stmt)]


class SQLAlchemyAlertRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, alert: ServerAlert) -> ServerAlert:
        model = AlertModel(
            server_id=alert.server_id,
            severity=alert.severity.value,
            message=alert.message,
            resolved=alert.resolved,
            created_at=alert.created_at,
            resolved_at=alert.resolved_at,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return to_alert(model)

    def find_active(self) -> list[ServerAlert]:
        stmt = select(AlertModel).where(AlertModel.resolved.is_(False)).order_by(AlertModel.created_at.desc())
        return [to_alert(m) for m in self.session.scalars(stmt)]

    def resolve(self, alert_id: int) -> bool:
        result = cast(
            CursorResult[Any],
            self.session.execute(
                update(AlertModel)
                .where(AlertModel.id == alert_id)
                .values(
                    resolved=True,
                    resolved_at=datetime.now(timezone.utc),
                )
            ),
        )
        self.session.commit()
        return result.rowcount == 1
