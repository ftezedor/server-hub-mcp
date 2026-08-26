from pydantic import BaseModel, Field

class ToolWarning(BaseModel):
    type: str
    message: str

class ServerReference(BaseModel):
    name: str
    ip: str


class ServerSummary(BaseModel):
    name: str
    ip: str
    environment: str
    status: str


class Metrics(BaseModel):
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    temperature_celsius: float | None = None
    uptime_seconds: int
    timestamp: str | None = None


class ServerDetails(ServerSummary):
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    last_updated: str | None = None
    created_at: str | None = None
    metrics: Metrics | None = None


class SearchServersResponse(BaseModel):
    query: str
    servers: list[ServerSummary]


class GetServerMetricsResponse(BaseModel):
    server: ServerReference
    metrics: list[Metrics]
    count: int


class Alert(BaseModel):
    server: ServerReference | None = None
    severity: str
    message: str
    created_at: str


class ActiveAlertsResponse(BaseModel):
    alerts: list[Alert]
    count: int
    warnings: list[ToolWarning] = Field(default_factory=list)


class SystemStatsResponse(BaseModel):
    total_servers: int
    servers_by_status: dict[str, int]
    active_alerts: int
    alerts_by_severity: dict[str, int]


class CreateAlertResponse(BaseModel):
    created: bool
    server: ServerReference
    severity: str
    message: str
    created_at: str | None = None