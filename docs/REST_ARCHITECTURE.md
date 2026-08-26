# REST/API Architecture

## Objective

The REST API is a first-class portfolio component of Server Hub. It follows a Ports & Adapters (Hexagonal) architecture so that the application and domain are independent from FastAPI and from the database technology.

SQLite is the default local database. PostgreSQL, Oracle, or another SQLAlchemy-supported relational database can be selected through `DATABASE_URL` without changing domain or application code.

## Architecture

```text
                    ┌─────────────────┐
                    │    REST API     │
                    │    FastAPI      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Application    │
                    │    Services     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Repository      │
                    │     Ports       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ SQLAlchemy      │
                    │ Persistence     │
                    │    Adapter      │
                    └────────┬────────┘
                             │
                 ┌───────────┼───────────┐
                 │           │           │
              SQLite     PostgreSQL    Oracle ...
```

The MCP interface can use the same application services. The database is therefore behind the same repository boundary regardless of the external interface.

## Layers

### Domain

`app/domain/` contains business concepts only:

- `Server`
- `ServerMetrics`
- `ServerAlert`
- `Environment`
- `ServerStatus`
- `AlertSeverity`
- domain exceptions

The domain does not import FastAPI, Pydantic, SQLAlchemy, SQLite, or MCP.

### Application

`app/application/` contains use cases and repository ports.

Services include:

- `ServerService`
- `MetricsService`
- `AlertService`
- `SystemService`

Repository protocols define what persistence can do without prescribing how it does it.

### Infrastructure

`app/infrastructure/persistence/sqlalchemy/` contains:

- SQLAlchemy ORM models;
- domain/ORM mappers;
- repository implementations;
- engine and session configuration.

SQLite is selected by default with:

```text
DATABASE_URL=sqlite:///./servers.db
```

A different SQLAlchemy-compatible relational database can be selected with its corresponding URL and driver.

### API

`app/api/` contains FastAPI routes and Pydantic request/response schemas.

Routes are intentionally thin. They translate HTTP requests into application service calls and map application/domain errors into HTTP responses.

## Database Independence

Application code depends on repository ports:

```python
class ServerRepository(Protocol):
    def find_by_id(self, server_id: int) -> Server | None: ...
    def find_by_name(self, name: str) -> Server | None: ...
    def search(self, query: str) -> list[Server]: ...
```

The current adapter is SQLAlchemy:

```text
ServerRepository
       ▲
       │
SQLAlchemyServerRepository
       │
       ▼
SQLAlchemy dialect
       │
SQLite / PostgreSQL / Oracle / ...
```

This means the domain and application layers do not change when the persistence technology changes.

## Schema-first API

Pydantic schemas expose important constraints directly through OpenAPI:

- server status and environment are enums;
- alert severity is an enum;
- metric percentages are constrained to `0..100`;
- metric history limit is constrained to `1..50`;
- names, messages, and numeric resources have explicit bounds.

The same principle was previously applied to the MCP tool contract.

## Compatibility

The REST endpoint shape remains compatible with the existing lab workflow, including:

- `/api/servers`
- `/api/servers/{server_id}`
- `/api/servers/{server_id}/status`
- `/api/servers/{server_id}/metrics`
- `/api/alerts`
- `/api/search`
- `/api/stats`

The legacy `database.py` module is retained only as a compatibility facade for older scripts. New application code must use services and repository ports.

## Testing Strategy

Testing is split by architectural boundary:

```text
Unit tests
    ↓
Application/domain behavior without a database

Integration tests
    ↓
Repository behavior using SQLAlchemy

API tests
    ↓
HTTP contract and validation
```

This prevents the majority of application tests from becoming dependent on SQLite.
