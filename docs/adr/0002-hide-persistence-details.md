# ADR-0002: Keep Persistence Details Behind the MCP Boundary

- **Status:** Accepted
- **Date:** 2026-08-26
- **Decision:** MCP clients use meaningful server identifiers and sanitized representations instead of persistence/database details.

## Context

Server Hub persistence uses internal database identifiers and internal entity relationships.

Exposing those details through MCP would couple MCP clients to the persistence implementation and make tool usage less natural for humans and LLMs.

For example, a client should be able to identify a server as:

```text
web-server-01
192.168.1.10
```

rather than needing an internal database ID.

The MCP v1 implementation already removes persistence identifiers from MCP-facing server representations and supports name/IP-based identification.

## Decision

MCP-facing operations use **meaningful domain identifiers** and expose **sanitized representations**.

### Server identity

Tools resolve:

```text
server name → internal server
server IP   → internal server
```

The internal persistence ID remains an implementation detail.

### Response boundary

Internal records are mapped into MCP-facing representations before being returned.

Conceptually:

```text
Database entity
      │
      ▼
Application/domain representation
      │
      ▼
MCP sanitization / mapping
      │
      ▼
MCP response
```

The same principle applies to nested objects such as alerts and metrics.

## Rationale

This creates a stable MCP contract independent of the database schema.

It also reduces unnecessary context sent to MCP clients and LLMs. Clients receive information relevant to the operational task rather than implementation metadata.

## Consequences

### Positive

- MCP clients are decoupled from database IDs.
- Database schema changes are less likely to break MCP clients.
- Tool calls are easier to formulate.
- Responses contain less irrelevant implementation detail.
- The MCP contract is easier to document and test.

### Negative

- Mapping code is required.
- REST and MCP representations may differ and require explicit equivalence tests.
- Some debugging scenarios require tracing an MCP entity back to an internal ID.

## Related

- `MCP_V1.md`
- `test_mcp.py`
- `test_api.py`
- `test_rest_mcp_equivalence.py`
