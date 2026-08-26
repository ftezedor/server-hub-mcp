from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MetricsCreate(BaseModel):
    cpu_usage_percent: float = Field(ge=0, le=100)
    memory_usage_percent: float = Field(ge=0, le=100)
    disk_usage_percent: float = Field(ge=0, le=100)
    temperature_celsius: float | None = None
    uptime_seconds: int = Field(ge=0)


class MetricsResponse(MetricsCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    server_id: int
    timestamp: datetime | None = None
