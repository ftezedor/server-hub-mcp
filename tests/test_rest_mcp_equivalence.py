# Version: 1.1
"""Black-box equivalence tests between the REST and MCP interfaces.

Both interfaces are exercised through their public transports.  The tests do
not import the FastAPI application or call MCP tool functions directly.

The REST API and MCP server must be running before this suite is executed.
Configure their URLs with:

    SERVER_HUB_API_URL=http://localhost:8080/api
    SERVER_HUB_MCP_URL=http://localhost:8000/mcp
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

from typing import Any, Generator

import httpx
import pytest
from fastmcp import Client


API_URL = os.getenv(
    "SERVER_HUB_API_URL",
    "http://localhost:8080/api",
).rstrip("/")
MCP_URL = os.getenv(
    "SERVER_HUB_MCP_URL",
    "http://localhost:8000/mcp",
).rstrip("/")
TIMEOUT = float(os.getenv("SERVER_HUB_TEST_TIMEOUT", "10"))


@pytest.fixture(scope="module")
def api() -> Generator[httpx.Client, None, None]:
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        yield client


def _mcp_call(tool: str, arguments: dict[str, Any] | None = None) -> Any:
    async def run() -> Any:
        async with Client(MCP_URL) as client:
            result = await client.call_tool(tool, arguments or {})
            return result

    return asyncio.run(run())


def _json_value(value: Any) -> Any:
    """Convert FastMCP result content into ordinary Python data."""
    if value is None:
        return None

    if isinstance(value, (dict, list, str, int, float, bool)):
        return value

    # FastMCP CallToolResult exposes structured_content when the server
    # returns a Pydantic model through FastMCP.
    structured = getattr(value, "structured_content", None)
    if structured:
        return structured

    content = getattr(value, "content", None)
    if content:
        values = []
        for item in content:
            text = getattr(item, "text", None)
            if text is not None:
                try:
                    values.append(json.loads(text))
                except (TypeError, json.JSONDecodeError):
                    values.append(text)
            else:
                values.append(item)
        if len(values) == 1:
            return values[0]
        return values

    # Older/newer FastMCP versions may expose the structured result through
    # a different attribute.  Keep the failure explicit instead of silently
    # comparing repr() output.
    raise AssertionError(f"Unable to extract MCP result: {value!r}")


def _mcp_json(tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    result = _json_value(_mcp_call(tool, arguments))
    assert isinstance(result, dict), f"Expected object from {tool}, got {result!r}"
    return result


def _server_by_name(api: httpx.Client, name: str) -> dict[str, Any]:
    response = api.get("/search", params={"q": name})
    response.raise_for_status()
    payload = response.json()
    matches = [item for item in payload["results"] if item["name"] == name]
    assert matches, f"REST API did not return server {name!r}"
    return matches[0]


def _choose_server(api: httpx.Client) -> dict[str, Any]:
    response = api.get("/servers")
    response.raise_for_status()
    payload = response.json()
    servers = payload["servers"]
    assert servers, "REST API returned no servers for equivalence testing"
    return servers[0]


def _normalise_server(server: dict[str, Any]) -> dict[str, Any]:
    return {
        key: server.get(key)
        for key in (
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
    }


def _normalise_metrics(metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    if metrics is None:
        return None
    return {
        key: metrics.get(key)
        for key in (
            "cpu_usage_percent",
            "memory_usage_percent",
            "disk_usage_percent",
            "temperature_celsius",
            "uptime_seconds",
            "timestamp",
        )
    }


def _normalise_alert(
    alert: dict[str, Any],
    servers_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    server = alert.get("server")

    if isinstance(server, dict):
        server_name = server.get("name")
        server_ip = server.get("ip")
    else:
        server_name = server
        server_ip = (
            servers_by_name.get(server_name, {}).get("ip")
            if servers_by_name and server_name
            else None
        )

    return {
        "server": server_name,
        "server_ip": server_ip,
        "severity": alert.get("severity"),
        "message": alert.get("message"),
        "created_at": alert.get("created_at"),
    }


def test_search_servers_is_equivalent(api: httpx.Client) -> None:
    server = _choose_server(api)
    query = server["name"]

    rest = api.get("/search", params={"q": query})
    rest.raise_for_status()
    rest_payload = rest.json()

    mcp_payload = _mcp_json("search_servers", {"query": query})

    rest_matches = [
        {
            key: item[key]
            for key in ("name", "ip", "environment", "status")
        }
        for item in rest_payload["results"]
        if item["name"] == query
    ]
    mcp_matches = [
        {
            key: item[key]
            for key in ("name", "ip", "environment", "status")
        }
        for item in mcp_payload["servers"]
        if item["name"] == query
    ]

    assert mcp_payload["query"] == rest_payload["query"]
    assert mcp_matches == rest_matches


def test_get_server_is_equivalent(api: httpx.Client) -> None:
    server = _choose_server(api)

    rest = api.get(f"/servers/{server['id']}")
    rest.raise_for_status()
    rest_payload = rest.json()

    mcp_payload = _mcp_json("get_server", {"server": server["name"]})

    assert _normalise_server(mcp_payload) == _normalise_server(rest_payload)
    assert _normalise_metrics(mcp_payload.get("metrics")) == _normalise_metrics(
        rest_payload.get("metrics")
    )


def test_get_server_metrics_is_equivalent(api: httpx.Client) -> None:
    server = _choose_server(api)
    limit = 5

    rest = api.get(
        f"/servers/{server['id']}/metrics",
        params={"limit": limit},
    )
    rest.raise_for_status()
    rest_payload = rest.json()

    mcp_payload = _mcp_json(
        "get_server_metrics",
        {"server": server["name"], "limit": limit},
    )

    assert mcp_payload["server"]["name"] == rest_payload["server"]["name"]
    assert mcp_payload["count"] == rest_payload["count"]

    rest_metrics = [
        _normalise_metrics(metric) for metric in rest_payload["metrics"]
    ]
    mcp_metrics = [
        _normalise_metrics(metric) for metric in mcp_payload["metrics"]
    ]
    assert mcp_metrics == rest_metrics


def test_get_active_alerts_is_equivalent(api: httpx.Client) -> None:
    rest = api.get("/alerts")
    rest.raise_for_status()
    rest_payload = rest.json()

    mcp_payload = _mcp_json("get_active_alerts")

    servers_response = api.get("/servers")
    servers_response.raise_for_status()
    servers_by_name = {
        server["name"]: server
        for server in servers_response.json()["servers"]
    }

    rest_alerts = [
        _normalise_alert(alert, servers_by_name)
        for alert in rest_payload["alerts"]
    ]
    mcp_alerts = [
        _normalise_alert(alert, servers_by_name)
        for alert in mcp_payload["alerts"]
    ]

    assert mcp_payload["count"] == rest_payload["total"]
    assert sorted(mcp_alerts, key=lambda item: (item["message"], item["created_at"] or "")) == sorted(
        rest_alerts,
        key=lambda item: (item["message"], item["created_at"] or ""),
    )


def test_get_system_stats_is_equivalent(api: httpx.Client) -> None:
    rest = api.get("/stats")
    rest.raise_for_status()
    rest_payload = rest.json()

    mcp_payload = _mcp_json("get_system_stats")

    assert mcp_payload == rest_payload



