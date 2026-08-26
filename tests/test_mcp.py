"""
Black-box MCP protocol tests.

These tests connect to the running MCP server through the MCP protocol.
They do not invoke app.mcp.server tool functions directly and do not use
mcp-cli.

Configuration:
    SERVER_HUB_MCP_URL=http://localhost:8000/mcp

Run:
    pytest -q tests/test_mcp.py
"""

import asyncio
import os

import pytest

try:
    from fastmcp import Client
except ImportError as exc:  # pragma: no cover - environment failure
    Client = None
    FASTMCP_IMPORT_ERROR = exc
else:
    FASTMCP_IMPORT_ERROR = None


MCP_URL = os.getenv(
    "SERVER_HUB_MCP_URL",
    "http://localhost:8000/mcp",
)


pytestmark = pytest.mark.asyncio


@pytest.fixture
def mcp_client():
    if Client is None:
        pytest.fail(f"fastmcp is required: {FASTMCP_IMPORT_ERROR}")
    return Client(MCP_URL)


async def call_tool(client, name, arguments=None):
    return await client.call_tool(name, arguments or {})


def tool_names(tools):
    return {
        getattr(tool, "name", None)
        for tool in tools
        if getattr(tool, "name", None)
    }


def result_payload(result):
    """
    Extract structured data when available, otherwise return text content.

    FastMCP has changed result representations between releases, so the test
    deliberately accepts the public result shapes rather than depending on a
    private implementation detail.
    """
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured

    data = getattr(result, "data", None)
    if data is not None:
        return data

    content = getattr(result, "content", None)
    if content:
        values = []
        for item in content:
            text = getattr(item, "text", None)
            if text is not None:
                values.append(text)
            else:
                values.append(item)
        return values[0] if len(values) == 1 else values

    return result


async def test_mcp_connection(mcp_client):
    async with mcp_client:
        tools = await mcp_client.list_tools()
        assert tools


async def test_all_six_tools_are_registered(mcp_client):
    async with mcp_client:
        tools = await mcp_client.list_tools()
        names = tool_names(tools)

    expected = {
        "search_servers",
        "get_server",
        "get_server_metrics",
        "get_active_alerts",
        "get_system_stats",
        "create_alert",
    }

    assert expected <= names
    assert len(names) == 6


async def test_search_servers(mcp_client):
    async with mcp_client:
        result = await call_tool(
            mcp_client,
            "search_servers",
            {"query": "web"},
        )

    payload = result_payload(result)

    assert payload is not None
    assert "web-server" in str(payload)


async def test_search_servers_rejects_empty_query(mcp_client):
    async with mcp_client:
        with pytest.raises(Exception):
            await call_tool(
                mcp_client,
                "search_servers",
                {"query": ""},
            )


async def test_get_server(mcp_client):
    async with mcp_client:
        result = await call_tool(
            mcp_client,
            "get_server",
            {"server": "web-server-01"},
        )

    payload = result_payload(result)

    assert "web-server-01" in str(payload)
    assert "192.168.1.10" in str(payload)


async def test_get_server_metrics(mcp_client):
    async with mcp_client:
        result = await call_tool(
            mcp_client,
            "get_server_metrics",
            {"server": "web-server-01", "limit": 5},
        )

    payload = result_payload(result)

    assert "web-server-01" in str(payload)
    assert "metrics" in str(payload)


async def test_get_server_metrics_rejects_invalid_limit(mcp_client):
    async with mcp_client:
        with pytest.raises(Exception):
            await call_tool(
                mcp_client,
                "get_server_metrics",
                {"server": "web-server-01", "limit": 0},
            )


async def test_get_active_alerts(mcp_client):
    async with mcp_client:
        result = await call_tool(mcp_client, "get_active_alerts")

    payload = result_payload(result)

    assert payload is not None
    assert "alerts" in str(payload)
    assert "count" in str(payload)


async def test_get_system_stats(mcp_client):
    async with mcp_client:
        result = await call_tool(mcp_client, "get_system_stats")

    payload = result_payload(result)

    assert "total_servers" in str(payload)
    assert "active_alerts" in str(payload)


async def test_create_alert_and_read_it(mcp_client):
    message = "MCP protocol test alert"

    async with mcp_client:
        created = await call_tool(
            mcp_client,
            "create_alert",
            {
                "server": "web-server-01",
                "severity": "warning",
                "message": message,
            },
        )

        created_payload = result_payload(created)
        assert "web-server-01" in str(created_payload)

        alerts = await call_tool(mcp_client, "get_active_alerts")

    alerts_payload = result_payload(alerts)

    assert message in str(alerts_payload)


async def test_create_alert_rejects_invalid_severity(mcp_client):
    async with mcp_client:
        with pytest.raises(Exception):
            await call_tool(
                mcp_client,
                "create_alert",
                {
                    "server": "web-server-01",
                    "severity": "invalid",
                    "message": "Should fail",
                },
            )


async def test_create_alert_rejects_empty_message(mcp_client):
    async with mcp_client:
        with pytest.raises(Exception):
            await call_tool(
                mcp_client,
                "create_alert",
                {
                    "server": "web-server-01",
                    "severity": "warning",
                    "message": "",
                },
            )


async def test_unknown_tool_is_rejected(mcp_client):
    async with mcp_client:
        with pytest.raises(Exception):
            await call_tool(
                mcp_client,
                "does_not_exist",
            )


async def test_prompts_are_discoverable(mcp_client):
    """
    The current Server Hub MCP server does not register custom prompts.

    This test verifies the protocol operation itself and deliberately does
    not require a prompt that the server does not currently expose.
    """
    async with mcp_client:
        prompts = await mcp_client.list_prompts()

    assert prompts is not None
