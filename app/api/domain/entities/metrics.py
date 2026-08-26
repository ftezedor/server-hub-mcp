from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ServerMetrics:
    server_id: int
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    uptime_seconds: int
    temperature_celsius: float | None = None
    id: int | None = None
    timestamp: datetime | None = None
