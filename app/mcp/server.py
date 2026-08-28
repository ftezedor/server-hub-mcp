"""Server Hub MCP adapter.

The MCP layer exposes a stable, agent-friendly interface over the Server Hub
application. Its backend can be either the REST API or the application layer
directly; both implementations satisfy the same client port.
"""

from __future__ import annotations

from app.mcp.playground import register_playground_routes

import json
import os
from typing import Annotated, Any, Literal, cast

from fastmcp import FastMCP
from pydantic import Field

from app.mcp.adapters import (
    AppServerHubClient,
    RestServerHubClient,
)
from app.mcp.contracts import ServerData
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

register_playground_routes(mcp)

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

def _as_mcp_timestamp(value: Any) -> str | None:
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)

def _clean_server_summary(server: ServerData) -> dict[str, Any]:
    """Return MCP-facing server data without the persistence ID."""
    return {
        "name": server.name,
        "ip": server.ip,
        "environment": server.environment,
        "status": server.status,
    }


def _clean_server(server: ServerData) -> dict[str, Any]:
    """Return MCP-facing server data without the persistence ID."""
    result: dict[str, Any] = {
        "name": server.name,
        "ip": server.ip,
        "environment": server.environment,
        "status": server.status,
        "cpu_cores": server.cpu_cores,
        "memory_gb": server.memory_gb,
        "disk_gb": server.disk_gb,
        "last_updated": server.last_updated,
        "created_at": server.created_at,
    }

    metrics = getattr(server, "metrics", None)

    if metrics is not None:
        result["metrics"] = metrics.model_dump(mode="json")
        
    return result


def _resolve_server(identifier: str) -> ServerData:
    """Resolve an exact server name or exact IP address.

    The client port intentionally exposes the persistence ID internally to
    the MCP adapter so it can call the corresponding backend operation.
    That ID is never exposed through an MCP response.
    """
    identifier = identifier.strip()

    if not identifier:
        raise ValueError("server must not be empty")

    data = client.search(identifier)

    exact = [
        server
        for server in data.results
        if server.name == identifier or server.ip == identifier
    ]

    if not exact:
        raise ValueError(f"Server '{identifier}' not found")

    if len(exact) > 1:
        raise ValueError(
            f"Server identifier '{identifier}' is ambiguous"
        )

    return exact[0]


# MCP resources


@mcp.resource(
    "server://{server}/details",
    name="server_details",
    description="Detailed information about a server.",
    mime_type="application/json",
)
def server_details_resource(server: str) -> str:
    """Read detailed information about one server."""
    resolved = _resolve_server(server)

    data = client.get_server_by_id(resolved.id)

    return json.dumps(
        _clean_server(data),
        ensure_ascii=False,
        default=str,
    )


@mcp.resource(
    "server://{server}/metrics",
    name="server_metrics",
    description="Recent metrics for a server.",
    mime_type="application/json",
)
def server_metrics_resource(server: str) -> str:
    """Read recent metrics for one server."""
    resolved = _resolve_server(server)

    data = client.get_metrics(resolved.id, 10)

    payload = {
        "server": {
            "name": data.server.name,
            "ip": resolved.ip,
        },
        "metrics": [
            metric.model_dump(mode="json")
            for metric in data.metrics
        ],
        "count": data.count,
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
    )


@mcp.resource(
    "server://{server}/alerts",
    name="server_alerts",
    description="Active alerts for a server.",
    mime_type="application/json",
)
def server_alerts_resource(server: str) -> str:
    """Read active alerts for one server."""
    resolved = _resolve_server(server)

    data = client.get_alerts()

    alerts = [
        alert.model_dump(mode="json")
        for alert in data.alerts
        if alert.server == resolved.name
        or alert.server_ip == resolved.ip
    ]

    payload = {
        "server": {
            "name": resolved.name,
            "ip": resolved.ip,
        },
        "alerts": alerts,
        "count": len(alerts),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
    )


@mcp.resource(
    "servers://active",
    name="active_servers",
    description="List all currently active servers.",
    mime_type="application/json",
)
def active_servers_resource() -> str:
    """Read the currently active servers."""
    data = client.list_servers()

    servers = [
        _clean_server_summary(server)
        for server in data.servers
        if server.status == "active"
    ]

    return json.dumps(
        {
            "servers": servers,
            "count": len(servers),
        },
        ensure_ascii=False,
    )


@mcp.resource(
    "system://stats",
    name="system_stats",
    description="Current aggregate system statistics.",
    mime_type="application/json",
)
def system_stats_resource() -> str:
    """Read aggregate system statistics."""
    return json.dumps(
        client.get_stats().model_dump(mode="json"),
        ensure_ascii=False,
    )


# MCP tools


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
            for server in data.results
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
            client.get_server_by_id(resolved.id)
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
    data = client.get_metrics(resolved.id, limit)

    return GetServerMetricsResponse(
        server=ServerReference(
            name=data.server.name,
            ip=resolved.ip,
        ),
        metrics=[
            Metrics.model_validate(metric.model_dump())
            for metric in data.metrics
        ],
        count=data.count,
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

    for raw_alert in data.alerts:
        if not raw_alert.server or not raw_alert.server_ip:
            warnings.append(
                ToolWarning(
                    type="server_reference_incomplete",
                    message="Alert is missing server name or IP address",
                )
            )

        server_ref = (
            ServerReference(
                name=raw_alert.server,
                ip=raw_alert.server_ip,
            )
            if raw_alert.server and raw_alert.server_ip
            else None
        )

        alerts.append(
            Alert(
                server=server_ref,
                severity=raw_alert.severity,
                message=raw_alert.message,
                created_at=raw_alert.created_at,
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
    return SystemStatsResponse(
        **client.get_stats().model_dump()
    )


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
        resolved.name,
        severity,
        message,
    )

    return CreateAlertResponse(
        created=True,
        server=ServerReference(
            name=resolved.name,
            ip=resolved.ip,
        ),
        severity=severity,
        message=message,
        created_at=(
            result.created_at
            if result.created_at is not None
            else None
        ),
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