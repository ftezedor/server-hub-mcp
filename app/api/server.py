#!/usr/bin/env python3
"""Server Hub REST API entry point.

FastAPI routes, application services and persistence are intentionally kept in
separate layers. SQLite is only the default persistence adapter; configure a
compatible SQLAlchemy database with DATABASE_URL.
"""
import argparse
import uvicorn
from main import app
from infrastructure.persistence.sqlalchemy import init_database


def run_http_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    init_database()
    print("=" * 60)
    print(f"🚀 Server Hub - REST API (port {port})")
    print("=" * 60)
    print(f"📖 Swagger UI:  http://{host}:{port}/docs")
    print(f"📚 ReDoc:       http://{host}:{port}/redoc")
    print(f"📋 OpenAPI:     http://{host}:{port}/openapi.json")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
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

    args = parser.parse_args()

    run_http_server(host=args.host, port=args.port)
