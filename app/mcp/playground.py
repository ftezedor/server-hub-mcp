"""Embedded MCP Playground HTTP routes.

The routes are registered directly on the existing FastMCP instance so the
normal mcp.run(transport="streamable-http", ...) startup path remains
unchanged.
"""

from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse

import app


PLAYGROUND_DIR = (
    Path(__file__).resolve().parents[2] / "app" / "www" / "playground"
)

print("========================")
print(PLAYGROUND_DIR)
print("========================")

def register_playground_routes(mcp: FastMCP) -> None:
    """Register the static Playground without changing MCP transport setup."""

    @mcp.custom_route(
        "/playground",
        methods=["GET"],
        include_in_schema=False,
    )
    async def playground_index(request: Request) -> FileResponse:
        return FileResponse(PLAYGROUND_DIR / "index.html")

    @mcp.custom_route(
        "/playground/{file_path:path}",
        methods=["GET"],
        include_in_schema=False,
    )
    async def playground_asset(
        request: Request,
    ) -> FileResponse | PlainTextResponse:
        requested = request.path_params["file_path"]
        candidate = (PLAYGROUND_DIR / requested).resolve()

        try:
            candidate.relative_to(PLAYGROUND_DIR.resolve())
        except ValueError:
            return PlainTextResponse("Not found", status_code=404)

        if not candidate.is_file():
            return PlainTextResponse("Not found", status_code=404)

        return FileResponse(candidate)
