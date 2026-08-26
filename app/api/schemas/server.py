from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.api.domain.enums import Environment, ServerStatus
from .metrics import MetricsResponse


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["web-server-01"])
    ip: str = Field(min_length=1, max_length=64, examples=["192.168.1.10"])
    environment: Environment
    status: ServerStatus = ServerStatus.ONLINE
    cpu_cores: int = Field(ge=1)
    memory_gb: float = Field(ge=1)
    disk_gb: float = Field(ge=1)


class ServerResponse(ServerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    last_updated: datetime | None = None
    created_at: datetime | None = None
    metrics: MetricsResponse | None = None


class ServerSummary(ServerResponse):
    pass
