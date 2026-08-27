from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


Severity = Literal["critical", "warning", "info"]


class ServerData(BaseModel):
    id: int
    name: str
    ip: str
    environment: str
    status: str
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    last_updated: str | None = None
    created_at: str | None = None


class ServerDetailsData(ServerData):
    metrics: MetricsData | None = None


class ServerReferenceData(BaseModel):
    id: int
    name: str


class MetricsData(BaseModel):
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    temperature_celsius: float | None = None
    uptime_seconds: int
    timestamp: str | None = None


class ServerMetricsData(BaseModel):
    server: ServerReferenceData
    metrics: list[MetricsData]
    count: int


class AlertData(BaseModel):
    id: int
    server: str | None
    server_ip: str | None
    severity: Severity
    message: str
    resolved: bool
    created_at: str
    resolved_at: str | None = None


class AlertsData(BaseModel):
    alerts: list[AlertData]
    total: int


class CreateAlertData(BaseModel):
    id: int
    message: str
    created_at: str | None = None


class ServerListData(BaseModel):
    servers: list[ServerData]
    total: int


class SearchData(BaseModel):
    query: str
    results: list[ServerData]
    count: int


class StatsData(BaseModel):
    total_servers: int
    servers_by_status: dict[str, int]
    active_alerts: int
    alerts_by_severity: dict[str, int]
