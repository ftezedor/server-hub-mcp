"""Server Hub MCP adapter.

The MCP layer exposes a stable, agent-friendly interface over the Server Hub
application. Its backend can be either the REST API or the application layer
directly; both implementations satisfy the same client port.
"""

from __future__ import annotations

import os, inspect
from typing import Annotated, Any, Literal, cast

from fastmcp import FastMCP
from pydantic import Field

from app.mcp.adapters import (
    AppServerHubClient,
    RestServerHubClient,
)
from app.mcp.models import (
    ActiveAlertsResponse,
    Alert,
    CreateAlertResponse,
    GetServerMetricsResponse,
    Metrics,
    SearchServersResponse,
    ServerDetails,
    ServerReference,
    ServerSummary,
    SystemStatsResponse,
    ToolWarning,
)
from app.mcp.ports import ServerHubClient


mcp = FastMCP("Server Hub")

VALID_SEVERITIES = {"critical", "warning", "info"}


def _build_client() -> ServerHubClient:
    
    backend = os.getenv("SERVER_HUB_MCP_BACKEND", "rest").strip().lower()

    if backend == "rest":
        return RestServerHubClient()

    if backend in {"application", "app", "direct"}:
        return AppServerHubClient()

    raise ValueError(
        "SERVER_HUB_MCP_BACKEND must be one of: rest, application"
    )


client: ServerHubClient = _build_client()


def _clean_server_summary(server: dict[str, Any]) -> dict[str, Any]:
    """Return MCP-facing server data without persistence IDs."""
    allowed = ("name", "ip", "environment", "status")
    return {
        key: server[key]
        for key in allowed
        if key in server
    }


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
    result = {
        key: server[key]
        for key in allowed
        if key in server
    }

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
    return {
        key: metrics[key]
        for key in allowed
        if key in metrics
    }


def _resolve_server(identifier: str) -> dict[str, Any]:
    """Resolve an exact server name or exact IP address.

    The client port intentionally exposes the persistence ID internally to
    the MCP adapter so it can call the corresponding backend operation.
    That ID is never exposed through an MCP response.
    """
    identifier = identifier.strip()

    if not identifier:
        raise ValueError("server must not be empty")

    data = client.search(identifier)
    results = data.get("results", [])

    exact = [
        server
        for server in results
        if server.get("name") == identifier
        or server.get("ip") == identifier
    ]

    if not exact:
        raise ValueError(f"Server '{identifier}' not found")

    if len(exact) > 1:
        raise ValueError(
            f"Server identifier '{identifier}' is ambiguous"
        )

    return exact[0]


@mcp.tool()
def search_servers(query: str) -> SearchServersResponse:
    """Search for servers by partial name or IP address.

    Use a meaningful search term. Empty queries and "*" are not supported.
    Returns lightweight summaries with name, IP, environment, and status.
    Use get_server when detailed information about one exact server is needed.
    """
    query = query.strip()

    if not query:
        raise ValueError("query must not be empty")

    data = client.search(query)

    return SearchServersResponse(
        query=query,
        servers=[
            ServerSummary(**_clean_server_summary(server))
            for server in data.get("results", [])
        ],
    )


@mcp.tool()
def get_server(server: str) -> ServerDetails:
    """Get detailed information about one server.

    The server argument must be the exact server name or exact IP address.
    Returns hardware information, status, timestamps, and current metrics.
    """
    resolved = _resolve_server(server)

    return ServerDetails(
        **_clean_server(
            client.get_server_by_id(resolved["id"])
        )
    )


@mcp.tool()
def get_server_metrics(
    server: str,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> GetServerMetricsResponse:
    """Get recent metric history for one server.

    The server argument must be the exact server name or exact IP address.
    limit specifies the number of metric records to return and must be 1-50.
    """
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    resolved = _resolve_server(server)
    data = client.get_metrics(resolved["id"], limit)

    return GetServerMetricsResponse(
        server=ServerReference(
            name=data.get("server", {}).get(
                "name",
                resolved["name"],
            ),
            ip=resolved["ip"],
        ),
        metrics=[
            Metrics(**_clean_metrics(metric))
            for metric in data.get("metrics", [])
        ],
        count=data.get("count", 0),
    )


@mcp.tool()
def get_active_alerts() -> ActiveAlertsResponse:
    """Get all currently active alerts across all servers.

    Returns each alert's server name, IP, severity, message, and creation time.
    This tool does not filter by server or environment.
    """
    data = client.get_alerts()
    alerts = []
    warnings = []

    for raw_alert in data.get("alerts", []):
        server_name = raw_alert.get("server")
        server_ip = raw_alert.get("server_ip")

        if not server_name or not server_ip:
            warnings.append(
                ToolWarning(
                    type="server_reference_incomplete",
                    message=(
                        "Alert is missing server name or IP address"
                    ),
                )
            )

        server_ref = (
            ServerReference(name=server_name, ip=server_ip)
            if server_name and server_ip
            else None
        )

        alerts.append(
            Alert(
                server=server_ref,
                severity=raw_alert["severity"],
                message=raw_alert["message"],
                created_at=raw_alert["created_at"],
            )
        )

    return ActiveAlertsResponse(
        alerts=alerts,
        count=len(alerts),
        warnings=warnings,
    )


@mcp.tool()
def get_system_stats() -> SystemStatsResponse:
    """Get aggregate system statistics.

    Returns server counts by status and active alert counts by severity.
    """
    return SystemStatsResponse(**client.get_stats())


@mcp.tool()
def create_alert(
    server: str,
    severity: Literal["critical", "warning", "info"],
    message: str,
) -> CreateAlertResponse:
    """Create a new active alert for a specific server.

    server must be the exact server name or exact IP address.
    severity must be one of: critical, warning, info.
    """
    normalized_severity = severity.strip().lower()
    message = message.strip()

    if normalized_severity not in VALID_SEVERITIES:
        raise ValueError(
            "severity must be one of: "
            + ", ".join(sorted(VALID_SEVERITIES))
        )

    if not message:
        raise ValueError("message must not be empty")

    severity = cast(
        Literal["critical", "warning", "info"],
        normalized_severity,
    )

    resolved = _resolve_server(server)
    result = client.create_alert(
        resolved["name"],
        severity,
        message,
    )

    return CreateAlertResponse(
        created=True,
        server=ServerReference(
            name=resolved["name"],
            ip=resolved["ip"],
        ),
        severity=severity,
        message=message,
        created_at=result.get("created_at"),
    )


def run_stdio() -> None:
    mcp.run(transport="stdio")


def run_http(host: str, port: int) -> None:
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    print(
        "Run local_server to start the stdio server or "
        "http_server to start the HTTP server.",
        flush=True,
    )
