from app.api.application.ports import AlertRepository, ServerRepository
from app.api.domain.enums import AlertSeverity, ServerStatus


class SystemService:
    def __init__(self, servers: ServerRepository, alerts: AlertRepository):
        self.servers = servers
        self.alerts = alerts

    def stats(self) -> dict:
        servers = self.servers.find_all()
        alerts = self.alerts.find_active()
        return {
            "total_servers": len(servers),
            "servers_by_status": {
                "online": sum(s.status == ServerStatus.ONLINE for s in servers),
                "offline": sum(s.status == ServerStatus.OFFLINE for s in servers),
                "maintenance": sum(s.status == ServerStatus.MAINTENANCE for s in servers),
            },
            "active_alerts": len(alerts),
            "alerts_by_severity": {
                "critical": sum(a.severity == AlertSeverity.CRITICAL for a in alerts),
                "warning": sum(a.severity == AlertSeverity.WARNING for a in alerts),
                "info": sum(a.severity == AlertSeverity.INFO for a in alerts),
            },
        }
