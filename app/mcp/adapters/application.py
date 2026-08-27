from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from app.api.container import services
from app.api.domain.entities import ServerAlert
from app.api.domain.enums import AlertSeverity


class AppServerHubClient:
    """Server Hub client backed directly by application services.

    This adapter is intended for an MCP server deployed in the same process
    or runtime as the REST application. It deliberately bypasses HTTP while
    preserving the same MCP-facing client contract.
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
    def _server_dict(server: Any) -> dict[str, Any]:
        result = {
            "id": server.id,
            "name": server.name,
            "ip": server.ip,
            "environment": server.environment.value,
            "status": server.status.value,
            "cpu_cores": server.cpu_cores,
            "memory_gb": server.memory_gb,
            "disk_gb": server.disk_gb,
            "last_updated": (
                server.last_updated.isoformat()
                if server.last_updated is not None
                else None
            ),
            "created_at": (
                server.created_at.isoformat()
                if server.created_at is not None
                else None
            ),
        }
        return result

    @staticmethod
    def _metrics_dict(metrics: Any) -> dict[str, Any]:
        return {
            "cpu_usage_percent": metrics.cpu_usage_percent,
            "memory_usage_percent": metrics.memory_usage_percent,
            "disk_usage_percent": metrics.disk_usage_percent,
            "temperature_celsius": metrics.temperature_celsius,
            "uptime_seconds": metrics.uptime_seconds,
            "timestamp": (
                metrics.timestamp.isoformat()
                if metrics.timestamp is not None
                else None
            ),
        }

    def search(self, query: str) -> dict[str, Any]:
        with self._services() as dep:
            servers = dep["servers"].search_servers(query)
            return {
                "query": query,
                "results": [
                    self._server_dict(server)
                    for server in servers
                ],
                "count": len(servers),
            }

    def get_server_by_id(self, server_id: int) -> dict[str, Any]:
        with self._services() as dep:
            server = dep["servers"].get_server(server_id)
            result = self._server_dict(server)
            latest = dep["metrics"].latest(server_id)
            result["metrics"] = (
                self._metrics_dict(latest)
                if latest is not None
                else None
            )
            return result

    def get_metrics(self, server_id: int, limit: int) -> dict[str, Any]:
        with self._services() as dep:
            server = dep["servers"].get_server(server_id)
            metrics = dep["metrics"].history(server_id, limit)
            return {
                "server": {
                    "id": server.id,
                    "name": server.name,
                },
                "metrics": [
                    self._metrics_dict(metric)
                    for metric in metrics
                ],
                "count": len(metrics),
            }

    def get_alerts(self) -> dict[str, Any]:
        with self._services() as dep:
            views = dep["alerts"].active()
            alerts = []

            for view in views:
                alerts.append(
                    {
                        "id": view.id,
                        "server": view.server,
                        "server_ip": view.server_ip,
                        "severity": view.severity.value,
                        "message": view.message,
                        "resolved": view.resolved,
                        "created_at": (
                            view.created_at.isoformat()
                            if view.created_at is not None
                            else None
                        ),
                        "resolved_at": (
                            view.resolved_at.isoformat()
                            if view.resolved_at is not None
                            else None
                        ),
                    }
                )

            return {
                "alerts": alerts,
                "total": len(alerts),
            }

    def get_stats(self) -> dict[str, Any]:
        with self._services() as dep:
            return dep["system"].stats()

    def create_alert(
        self,
        server: str,
        severity: str,
        message: str,
    ) -> dict[str, Any]:
        with self._services() as dep:
            alert = dep["alerts"].create(
                server=server,
                severity=AlertSeverity(severity),
                message=message,
            )
            return {
                "id": alert.id,
                "message": "Alerta criado com sucesso",
                "created_at": (
                    alert.created_at.isoformat()
                    if alert.created_at is not None
                    else None
                ),
            }

    def list_servers(self) -> dict[str, Any]:
        with self._services() as dep:
            servers = dep["servers"].list_servers()
            return {
                "servers": [
                    self._server_dict(server)
                    for server in servers
                ],
                "total": len(servers),
            }