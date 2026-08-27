from __future__ import annotations

from typing import Protocol

from app.mcp.contracts import (
    AlertsData,
    CreateAlertData,
    SearchData,
    ServerData,
    ServerDetailsData,
    ServerListData,
    ServerMetricsData,
    StatsData,
)

class ServerHubClient(Protocol):
    """Backend port used by MCP tools.

    Implementations may obtain data over HTTP or directly from the application
    layer. The MCP tools depend only on this contract.
    """

    def search(self, query: str) -> SearchData: ...

    def get_server_by_id(self, server_id: int) -> ServerDetailsData: ...

    def get_metrics(self, server_id: int, limit: int) -> ServerMetricsData: ...

    def get_alerts(self) -> AlertsData: ...

    def get_stats(self) -> StatsData: ...

    def create_alert(
        self,
        server: str,
        severity: str,
        message: str,
    ) -> CreateAlertData: ...

    def list_servers(self) -> ServerListData: ...