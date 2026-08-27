# ADR-0019: MCP Backend Abstraction

- Status: Accepted
- Date: 2026-08-27

## Context

The Server Hub MCP server can obtain backend data through two different execution paths:

1. REST API
2. Application layer directly

The MCP layer should not depend on either implementation.

The project therefore defines the `ServerHubClient` port as the abstraction between MCP tools, resources, and the backend.

The two current implementations are:

- `RestServerHubClient`
- `AppServerHubClient`

Both implementations expose the same typed contract through the models defined in `app/mcp/contracts.py`.

This allows the MCP interface to remain independent of how the underlying Server Hub functionality is accessed.

## Decision

We will keep the MCP backend behind the `ServerHubClient` protocol.

The MCP layer will depend only on:

```text
ServerHubClient
      │
      ├── RestServerHubClient
      │
      └── AppServerHubClient
```

The backend is selected through the `SERVER_HUB_MCP_BACKEND` environment variable.

Supported values are:

- `rest` — communicate with the Server Hub REST API.
- `application` — invoke the application layer directly.

The adapters are responsible for translating their respective backend representations into the typed MCP contracts.

The MCP layer must not:

- perform REST requests directly;
- access application services directly;
- depend on persistence or domain implementation details;
- rely on untyped dictionaries returned by the backend.

## Rationale

This separation provides several benefits.

### Backend independence

The MCP interface remains unchanged when the backend access mechanism changes.

### Deployment flexibility

The MCP server can run as an independent process using the REST API, or alongside the application and invoke the application layer directly.

### Testability

The MCP layer can be tested against the `ServerHubClient` abstraction without requiring a specific backend implementation.

### Type safety

Both adapters translate their backend responses into explicit Pydantic contracts before returning them to the MCP layer.

### Future extensibility

Additional backend implementations can be introduced without changing MCP tools or resources, provided they implement `ServerHubClient`.

## Consequences

### Positive

- MCP code is decoupled from backend implementation details.
- REST and in-process execution can coexist.
- Backend implementations can evolve independently.
- Typed contracts make the boundary explicit.
- The architecture supports future backend implementations.

### Negative

- The project has an additional abstraction layer.
- Backend adapters require translation between their native models and MCP contracts.
- Changes to the `ServerHubClient` contract may require updates to multiple adapters.

These costs are intentional because the MCP layer is an integration boundary and benefits from remaining independent of the backend execution mechanism.

## Alternatives Considered

### MCP directly calls the REST API

Rejected because it couples MCP to a specific deployment architecture and prevents efficient in-process execution.

### MCP directly calls application services

Rejected because it couples the MCP layer to the application's internal implementation and makes independent deployment more difficult.

### Separate MCP implementations for each backend

Rejected because it would duplicate MCP tools, resources, and behavior and increase the risk of divergence.

## Related Changes

This decision is implemented by:

- `app/mcp/ports.py`
- `app/mcp/contracts.py`
- `app/mcp/adapters/rest.py`
- `app/mcp/adapters/application.py`
- `app/mcp/server.py`
