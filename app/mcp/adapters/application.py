from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from app.api.container import services
from app.api.domain.enums import AlertSeverity
from app.mcp.contracts import (
    AlertData,
    AlertsData,
    CreateAlertData,
    MetricsData,
    SearchData,
    ServerData,
    ServerDetailsData,
    ServerListData,
    ServerMetricsData,
    ServerReferenceData,
    StatsData,
)


class AppServerHubClient:
    """Server Hub client backed directly by application services.

    This adapter bypasses HTTP while preserving the same MCP-facing
    ServerHubClient contract as the REST adapter.
    """

    def __init__(self) -> None:
        print("Local Server Hub API")

    @contextmanager
    def _services(self) -> Iterator[dict[str, Any]]:
        dependency_generator = services()

        try:
            yield next(dependency_generator)
        finally:
            dependency_generator.close()

    @staticmethod
    def _server_data(server: Any) -> ServerData:
        return ServerData(
            id=server.id,
            name=server.name,
            ip=server.ip,
            environment=server.environment.value,
            status=server.status.value,
            cpu_cores=server.cpu_cores,
            memory_gb=server.memory_gb,
            disk_gb=server.disk_gb,
            last_updated=(
                server.last_updated.isoformat()
                if server.last_updated is not None
                else None
            ),
            created_at=(
                server.created_at.isoformat()
                if server.created_at is not None
                else None
            ),
        )

    @staticmethod
    def _metrics_data(metrics: Any) -> MetricsData:
        return MetricsData(
            cpu_usage_percent=metrics.cpu_usage_percent,
            memory_usage_percent=metrics.memory_usage_percent,
            disk_usage_percent=metrics.disk_usage_percent,
            temperature_celsius=metrics.temperature_celsius,
            uptime_seconds=metrics.uptime_seconds,
            timestamp=(
                metrics.timestamp.isoformat()
                if metrics.timestamp is not None
                else None
            ),
        )

    @staticmethod
    def _alert_data(view: Any) -> AlertData:
        return AlertData(
            id=view.id,
            server=view.server,
            server_ip=view.server_ip,
            severity=view.severity.value,
            message=view.message,
            resolved=view.resolved,
            created_at=view.created_at.isoformat(),
            resolved_at=(
                view.resolved_at.isoformat()
                if view.resolved_at is not None
                else None
            ),
        )

    def search(self, query: str) -> SearchData:
        with self._services() as dep:
            servers = dep["servers"].search_servers(query)

            return SearchData(
                query=query,
                results=[self._server_data(server) for server in servers],
                count=len(servers),
            )

    def get_server_by_id(self, server_id: int) -> ServerDetailsData:
        with self._services() as dep:
            server = dep["servers"].get_server(server_id)
            metrics = dep["metrics"].latest(server_id)

            return ServerDetailsData(
                **self._server_data(server).model_dump(),
                metrics=(
                    self._metrics_data(metrics)
                    if metrics is not None
                    else None
                ),
            )

    def get_metrics(self, server_id: int, limit: int) -> ServerMetricsData:
        with self._services() as dep:
            server = dep["servers"].get_server(server_id)
            metrics = dep["metrics"].history(server_id, limit)

            return ServerMetricsData(
                server=ServerReferenceData(id=server.id, name=server.name),
                metrics=[self._metrics_data(metric) for metric in metrics],
                count=len(metrics),
            )

    def get_alerts(self) -> AlertsData:
        with self._services() as dep:
            views = dep["alerts"].active()

            return AlertsData(
                alerts=[self._alert_data(view) for view in views],
                total=len(views),
            )

    def get_stats(self) -> StatsData:
        with self._services() as dep:
            return StatsData.model_validate(dep["system"].stats())

    def create_alert(
        self,
        server: str,
        severity: str,
        message: str,
    ) -> CreateAlertData:
        with self._services() as dep:
            alert = dep["alerts"].create(
                server=server,
                severity=AlertSeverity(severity),
                message=message,
            )

            return CreateAlertData(
                id=alert.id,
                message="Alerta criado com sucesso",
                created_at=(
                    alert.created_at.isoformat()
                    if alert.created_at is not None
                    else None
                ),
            )

    def list_servers(self) -> ServerListData:
        with self._services() as dep:
            servers = dep["servers"].list_servers()

            return ServerListData(
                servers=[self._server_data(server) for server in servers],
                total=len(servers),
            )
