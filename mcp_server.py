"""Server Hub MCP adapter.

The MCP layer exposes a stable, agent-friendly interface over the existing
Server Hub REST API. REST/database implementation details (especially IDs)
are intentionally hidden from MCP clients.
"""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

import httpx
from fastmcp import FastMCP
from pydantic import Field

API_BASE_URL = os.getenv("SERVER_HUB_API_URL", "http://localhost:8080/api").rstrip("/")
DEFAULT_TIMEOUT = float(os.getenv("SERVER_HUB_API_TIMEOUT", "10"))

mcp = FastMCP("Server Hub")


class ServerHubClient:
    """Small REST client used exclusively by the MCP adapter."""

    def __init__(self, base_url: str = API_BASE_URL, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)
            raise RuntimeError(f"Server Hub API error ({exc.response.status_code}): {detail}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Unable to reach Server Hub API: {exc}") from exc

    def search(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/search", params={"q": query})

    def get_server_by_id(self, server_id: int) -> dict[str, Any]:
        return self._request("GET", f"/servers/{server_id}")

    def get_metrics(self, server_id: int, limit: int) -> dict[str, Any]:
        return self._request("GET", f"/servers/{server_id}/metrics", params={"limit": limit})

    def get_alerts(self) -> dict[str, Any]:
        return self._request("GET", "/alerts")

    def get_stats(self) -> dict[str, Any]:
        return self._request("GET", "/stats")

    def create_alert(self, server_id: int, severity: str, message: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/alerts",
            json={"server_id": server_id, "severity": severity, "message": message},
        )


client = ServerHubClient()


VALID_SEVERITIES = {"critical", "warning", "info"}


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            return str(payload["detail"])
    except ValueError:
        pass
    return response.text or response.reason_phrase


def _clean_server_summary(server: dict[str, Any]) -> dict[str, Any]:
    """Return MCP-facing server data without persistence IDs."""
    allowed = (
        "name",
        "ip",
        "environment",
        "status"
    )
    result = {key: server[key] for key in allowed if key in server}
    return result


def _clean_server(server: dict[str, Any]) -> dict[str, Any]:
    """Return MCP-facing server data without persistence IDs."""
    allowed = (
        "name",
        "ip",
        "environment",
        "status",
        "cpu_cores",
        "memory_gb",
        "disk_gb",
        "last_updated",
        "created_at",
    )
    result = {key: server[key] for key in allowed if key in server}
    if server.get("metrics") is not None:
        result["metrics"] = _clean_metrics(server["metrics"])
    return result


def _clean_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "cpu_usage_percent",
        "memory_usage_percent",
        "disk_usage_percent",
        "temperature_celsius",
        "uptime_seconds",
        "timestamp",
    )
    return {key: metrics[key] for key in allowed if key in metrics}


def _resolve_server(identifier: str) -> dict[str, Any]:
    """Resolve an exact server name or exact IP address.

    The REST API only offers partial search, so the MCP layer performs the
    exact-match check itself. IDs never cross the MCP boundary.
    """
    identifier = identifier.strip()
    if not identifier:
        raise ValueError("server must not be empty")

    data = client.search(identifier)
    results = data.get("results", [])
    exact = [
        server
        for server in results
        if server.get("name") == identifier or server.get("ip") == identifier
    ]

    if not exact:
        raise ValueError(f"Server '{identifier}' not found")
    if len(exact) > 1:
        raise ValueError(f"Server identifier '{identifier}' is ambiguous")

    return exact[0]


@mcp.tool()
def search_servers(query: str) -> dict[str, Any]:
    """Search for servers by partial name or IP address.

    Use a meaningful search term. Empty queries and "*" are not supported.
    Returns lightweight summaries with name, IP, environment, and status.
    Use get_server when detailed information about one exact server is needed.
    """
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    data = client.search(query)
    return {
        "query": query,
        "servers": [_clean_server_summary(server) for server in data.get("results", [])],
    }


@mcp.tool()
def get_server(server: str) -> dict[str, Any]:
    """Get detailed information about one server.

    The server argument must be the exact server name or exact IP address.
    Returns hardware information, status, timestamps, and current metrics.
    Use search_servers first when the exact name or IP is unknown.
    Server status represents the server's operational state. 
    An online server may still have active alerts. 
    Use get_active_alerts to determine alert conditions.
    """
    resolved = _resolve_server(server)
    return _clean_server(client.get_server_by_id(resolved["id"]))


@mcp.tool()
def get_server_metrics(
    server: str, 
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Get recent metric history for one server.

    The server argument must be the exact server name or exact IP address.
    limit specifies the number of metric records to return and must be 1-50.
    Use this tool when historical or recent performance measurements are needed.
    """
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    resolved = _resolve_server(server)
    data = client.get_metrics(resolved["id"], limit)
    return {
        "server": {
            "name": data.get("server", {}).get("name", resolved["name"]),
            "ip": resolved.get("ip"),
        },
        "metrics": [_clean_metrics(metric) for metric in data.get("metrics", [])],
        "count": data.get("count", 0),
    }


@mcp.tool()
def get_active_alerts() -> dict[str, Any]:
    """Get all currently active alerts across all servers.

    Returns each alert's server name, IP, severity, message, and creation time.
    This tool does not filter by server or environment.
    """
    data = client.get_alerts()
    alerts = []

    for alert in data.get("alerts", []):
        server = client.get_server_by_id(alert["server_id"])
        alerts.append(
            {
                "server": {
                    "name": server.get("name"),
                    "ip": server.get("ip"),
                },
                "severity": alert.get("severity"),
                "message": alert.get("message"),
                "created_at": alert.get("created_at"),
            }
        )

    return {"alerts": alerts, "count": len(alerts)}


@mcp.tool()
def get_system_stats() -> dict[str, Any]:
    """Get aggregate system statistics.

    Returns server counts by status and active alert counts by severity.
    Use this for an overall system health summary rather than details about
    a specific server.
    """
    return client.get_stats()


@mcp.tool()
def create_alert(
    server: str, 
    severity: Literal["critical", "warning", "info"],
    message: str
) -> dict[str, Any]:
    """Create a new active alert for a specific server.

    server must be the exact server name or exact IP address.
    severity must be one of: critical, warning, info.
    This operation modifies system state.
    """
    severity = severity.strip().lower()
    message = message.strip()

    if severity not in VALID_SEVERITIES:
        raise ValueError(f"severity must be one of: {', '.join(sorted(VALID_SEVERITIES))}")
    if not message:
        raise ValueError("message must not be empty")

    resolved = _resolve_server(server)
    result = client.create_alert(resolved["id"], severity, message)

    # Deliberately omit the REST/database alert ID from the MCP contract.
    return {
        "created": True,
        "server": {
            "name": resolved["name"],
            "ip": resolved["ip"],
        },
        "severity": severity,
        "message": message,
        "created_at": result.get("created_at"),
    }


def run_stdio() -> None:
    mcp.run(transport="stdio")


def run_http() -> None:
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run_stdio()
