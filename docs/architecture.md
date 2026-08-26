# Architecture

## System Context

Server Hub exposes the same operational capabilities through two public interfaces:
REST and MCP.

```mermaid
flowchart LR
    RESTClient["REST Client"] --> REST["REST API"]
    MCPClient["MCP Client / AI Agent"] --> MCP["MCP Server"]

    REST --> App["Application Layer"]
    MCP --> App

    App --> Domain["Domain / Models"]
    App --> Repo["Persistence / Repository"]
    Repo --> DB[("Database")]

    App --> External["Infrastructure Data / Services"]
```

## Interface Architecture

The REST and MCP interfaces are adapters over the same application capabilities.

```mermaid
flowchart TB
    subgraph Clients
        Browser["REST Consumer"]
        Agent["MCP Client / AI Agent"]
    end

    subgraph Interfaces
        REST["REST Adapter"]
        MCP["MCP Adapter"]
    end

    subgraph Application
        Services["Application Services"]
        Models["Domain Models"]
    end

    subgraph Infrastructure
        Persistence["Repositories / Persistence"]
        Data["Server / Metrics / Alert Data"]
    end

    Browser --> REST
    Agent --> MCP

    REST --> Services
    MCP --> Services

    Services --> Models
    Services --> Persistence
    Persistence --> Data
```

## MCP Tool Surface

The MCP adapter exposes the following six tools:

```mermaid
flowchart LR
    MCP["MCP Server"]

    MCP --> Search["search_servers"]
    MCP --> Server["get_server"]
    MCP --> Metrics["get_server_metrics"]
    MCP --> Alerts["get_active_alerts"]
    MCP --> Stats["get_system_stats"]
    MCP --> Create["create_alert"]
```

## Architectural Principles

- REST and MCP are interface adapters, not separate business-logic implementations.
- Application capabilities are shared by both interfaces.
- Persistence details remain behind the application boundary.
- MCP responses expose sanitized, client-oriented representations.
- REST ↔ MCP equivalence tests verify that both interfaces expose equivalent capabilities and data.

## Related Documentation

- `docs/adr/0001-mcp-as-interface-adapter.md`
- `docs/adr/0002-hide-persistence-details.md`
- `tests/test_api.py`
- `tests/test_mcp.py`
- `tests/test_rest_mcp_equivalence.py`
