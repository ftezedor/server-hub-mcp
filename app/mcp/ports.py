from __future__ import annotations

from typing import Any, Protocol


class ServerHubClient(Protocol):
    """Backend port used by MCP tools.

    Implementations may obtain data over HTTP or directly from the application
    layer. The MCP tools depend only on this contract.
    """

    def search(self, query: str) -> dict[str, Any]: ...

    def get_server_by_id(self, server_id: int) -> dict[str, Any]: ...

    def get_metrics(self, server_id: int, limit: int) -> dict[str, Any]: ...

    def get_alerts(self) -> dict[str, Any]: ...

    def get_stats(self) -> dict[str, Any]: ...

    def create_alert(
        self,
        server: str,
        severity: str,
        message: str,
    ) -> dict[str, Any]: ...

    def list_servers(self) -> dict[str, Any]: ...