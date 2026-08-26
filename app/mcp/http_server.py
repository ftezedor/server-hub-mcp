"""HTTP transport launcher for the canonical Server Hub MCP server."""

import argparse

from app.mcp.server import run_http


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Server Hub MCP HTTP server."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP server port (default: 8080)",
    )
    parser.add_argument(
        "--transport",
        default="http",
        help="Transport protocol (default: http)",
    )

    args = parser.parse_args()

    run_http(host=args.host, port=args.port)


if __name__ == "__main__":
    main()