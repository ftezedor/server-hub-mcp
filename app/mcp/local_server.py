"""HTTP transport launcher for the canonical Server Hub MCP server."""

from app.mcp.server import run_stdio


if __name__ == "__main__":
    run_stdio()
