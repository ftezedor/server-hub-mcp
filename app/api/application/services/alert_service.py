from app.api.application.ports import AlertRepository
from app.api.application.services.server_service import ServerService
from app.api.domain.entities import ServerAlert
from app.api.domain.enums import AlertSeverity
from app.api.application.dto import AlertView


class AlertService:
    def __init__(
        self,
        repository: AlertRepository,
        servers: ServerService,
    ):
        self.repository = repository
        self.servers = servers

    def create(
        self,
        server: str,
        severity: AlertSeverity,
        message: str,
    ) -> ServerAlert:
        server_entity = self.servers.find_by_identifier(server)

        alert = ServerAlert(
            server_id=server_entity.id,
            severity=severity,
            message=message,
        )

        return self.repository.save(alert)

    def active(self) -> list[AlertView]:
        alerts = self.repository.find_active()

        result = []

        for alert in alerts:
            server = self.servers.find_by_id(alert.server_id)

            if server is None:
                continue

            result.append(
                AlertView(
                    id=alert.id,
                    server=server.name,
                    server_ip=server.ip,
                    severity=alert.severity,
                    message=alert.message,
                    resolved=alert.resolved,
                    created_at=alert.created_at,
                    resolved_at=alert.resolved_at,
                )
            )

        return result

    def resolve(self, alert_id: int) -> bool:
        return self.repository.resolve(alert_id)