from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Server(BaseModel):
    id: Optional[int] = None
    name: str
    ip: str
    environment: str  # production, staging, development
    status: str       # online, offline, maintenance
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None

class ServerMetrics(BaseModel):
    id: Optional[int] = None
    server_id: int
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    temperature_celsius: Optional[float] = None
    uptime_seconds: int
    timestamp: Optional[datetime] = None

class ServerAlert(BaseModel):
    id: Optional[int] = None
    server_id: int
    severity: str  # critical, warning, info
    message: str
    resolved: bool = False
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None