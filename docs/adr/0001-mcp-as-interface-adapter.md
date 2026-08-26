# ADR-0001: Treat MCP as an Interface Adapter

- **Status:** Accepted
- **Date:** 2026-08-26
- **Decision:** MCP is an adapter/interface layer over Server Hub application capabilities.

## Context

Server Hub exposes infrastructure information and operational actions through both REST and MCP.

The MCP layer must remain independent from persistence details and should not become a second implementation of the application's business logic. The project documentation identifies separation between the MCP interface, application/business logic, and persistence as a core architectural principle.

The MCP tool set is intentionally small and composable:

- `search_servers`
- `get_server`
- `get_server_metrics`
- `get_active_alerts`
- `get_system_stats`
- `create_alert`

## Decision

The MCP server is treated as a **first-class interface adapter**.

Its responsibilities are:

1. Accept MCP tool requests.
2. Validate and resolve MCP-facing identifiers.
3. Invoke application capabilities through the appropriate application boundary.
4. Sanitize internal data before exposing it through MCP.
5. Return MCP-oriented responses.

Business rules and persistence concerns remain outside the MCP layer.

REST and MCP should therefore converge on the same application behavior rather than implementing parallel business logic.

```text
                 REST API
                    │
                    ▼
             Application Layer
                    ▲
                    │
                 MCP Adapter
                    ▲
                    │
                MCP Client
```

## Rationale

This keeps MCP replaceable and prevents the protocol from leaking into the domain/application implementation.

It also makes the same capabilities reusable by other interfaces in the future, such as a CLI, web UI, or AI agent.

## Consequences

### Positive

- Clear separation of concerns.
- Less duplication between REST and MCP.
- Easier unit and integration testing.
- MCP remains focused on protocol adaptation.
- Easier future integration with MCP clients and AI agents.

### Negative

- An additional application boundary must be maintained.
- Some operations require explicit mapping between application and MCP representations.
- Changes to application contracts may require MCP adapter changes.

## Related

- `MCP_V1.md`
- REST ↔ MCP equivalence tests
- `test_mcp.py`
