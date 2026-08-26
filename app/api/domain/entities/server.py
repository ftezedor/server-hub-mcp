from dataclasses import dataclass
from datetime import datetime
from app.api.domain.enums import Environment, ServerStatus


@dataclass(slots=True)
class Server:
    name: str
    ip: str
    environment: Environment
    status: ServerStatus
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    id: int | None = None
    last_updated: datetime | None = None
    created_at: datetime | None = None
