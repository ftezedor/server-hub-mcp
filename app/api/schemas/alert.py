from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.api.domain.enums import AlertSeverity


class AlertCreate(BaseModel):
    server: str = Field(min_length=1, max_length=255)
    severity: AlertSeverity
    message: str = Field(min_length=1, max_length=2000)


class AlertResponse(AlertCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    server_ip: str | None = None
    resolved: bool
    created_at: datetime | None = None
    resolved_at: datetime | None = None
