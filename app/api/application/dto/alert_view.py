from dataclasses import dataclass
from datetime import datetime

from app.api.domain.enums import AlertSeverity


@dataclass(frozen=True)
class AlertView:
    id: int
    server: str
    server_ip: str
    severity: AlertSeverity
    message: str
    resolved: bool
    created_at: datetime
    resolved_at: datetime | None