from dataclasses import dataclass
from datetime import datetime
from app.api.domain.enums import AlertSeverity


@dataclass(slots=True)
class ServerAlert:
    server_id: int
    severity: AlertSeverity
    message: str
    resolved: bool = False
    id: int | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None
