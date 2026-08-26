# Server Hub MCP v1

## 1. Overview

Server Hub is an MCP (Model Context Protocol) server that exposes server-infrastructure information and operational actions to MCP clients and LLMs.

The goal of the first version is to provide a small, reliable, model-friendly toolset while keeping persistence details and database identifiers behind the MCP boundary.

This document records the architecture, decisions, tests, fixes, and deliberate backlog items completed during the MCP v1 implementation.

## 2. MCP v1 Goals

- Expose server inventory and operational data through MCP.
- Hide persistence/database IDs from MCP clients.
- Allow server identification by name or IP address.
- Support partial server searches and fleet-wide discovery.
- Provide clean, predictable MCP-facing responses.
- Expose meaningful input constraints through MCP schemas.
- Validate invalid input consistently.
- Support multiple MCP clients and reconnects.
- Enable LLMs to compose tools for operational reasoning.
- Ground LLM responses in data returned by MCP tools.

## 3. Architecture

```text
                  ┌──────────────────────┐
                  │      MCP Client      │
                  │  mcp-cli / LLM app  │
                  └──────────┬───────────┘
                             │
                         MCP protocol
                             │
                  ┌──────────▼───────────┐
                  │      Server Hub      │
                  │      MCP Server      │
                  ├──────────────────────┤
                  │ Tool layer           │
                  │ Validation           │
                  │ Identity resolution  │
                  │ Response sanitizing  │
                  └──────────┬───────────┘
                             │
                       persistence layer
                             │
                  ┌──────────▼───────────┐
                  │       Database       │
                  │ internal IDs, data  │
                  └──────────────────────┘
```

The MCP layer is an abstraction boundary. Clients should not need database primary keys, persistence implementation details, or internal entity relationships.

## 4. Tool Inventory

| Tool | Purpose |
|---|---|
| `search_servers` | Search servers by partial name or IP |
| `get_server` | Retrieve detailed information for one server |
| `get_server_metrics` | Retrieve recent metrics for one server |
| `get_active_alerts` | Retrieve currently active alerts |
| `get_system_stats` | Retrieve aggregate system statistics |
| `create_alert` | Create an active alert for a server |

The tool set deliberately remains small. The objective is to provide composable operational primitives rather than expose every database/API operation.

## 5. Server Identity

### Decision

MCP clients must not deal with internal persistence IDs.

Tools accept meaningful identifiers such as a server name or IP address. Server Hub resolves that identifier to the corresponding internal record.

For example:

```text
get_server("web-server-01")
get_server("192.168.1.10")
```

Both resolve to the same server.

### Rationale

This keeps database implementation details behind the MCP boundary and makes tools easier for both humans and LLMs to use.

## 6. Search Semantics

`search_servers` supports partial matching by name/IP and fleet-wide discovery when a question requires cross-server analysis.

This enables workflows such as:

```text
search_servers
    ↓
discover fleet
    ↓
get_server_metrics for relevant servers
    ↓
compare metrics
```

without requiring a separate "list all servers" tool.

## 7. MCP-Facing Response Sanitization

Internal database records and MCP representations are deliberately different.

Persistence IDs are removed from MCP-facing server data through helpers such as:

- `_clean_server()`
- `_clean_server_summary()`

Conceptually:

```text
Database object
    ↓
_clean_server()
    ↓
MCP-facing server object
```

This reduces client/database coupling and avoids unnecessary implementation details entering the LLM context.

## 8. Tool Input Schemas

Important constraints were moved from prose into the MCP schema.

### `get_server_metrics`

`limit` is represented structurally as:

```text
type: integer
minimum: 1
maximum: 50
default: 10
```

### `create_alert`

`severity` is represented as:

```text
critical
warning
info
```

The implementation also validates these values at runtime.

**Principle:** the schema is the contract; descriptions explain intent; runtime validation enforces the contract.

## 9. Validation and Error Handling

Explicit invalid-input tests were performed.

### Unknown server

```text
get_server({"server": "does-not-exist"})
```

and an unknown IP both produce clear not-found errors.

### Empty search

```text
search_servers({"query": ""})
```

is rejected because the search query must be meaningful.

### Invalid metrics limit

Values outside `1..50`, including `0` and `999`, are rejected.

### Invalid alert severity

Values other than `critical`, `warning`, and `info` are rejected.

### Missing required argument

Calling `get_server({})` produces schema validation indicating that `server` is required.

## 10. MCP Protocol Validation

The MCP server was tested using `mcp-cli`.

Initialization succeeds and repeated connections return the same six-tool contract. The raw tool listing was inspected to verify that generated schemas include the intended constraints.

**Result: PASS**

## 11. MCP Lifecycle and Resilience

### Restart / reconnect

The server was restarted and an MCP client successfully reconnected.

**PASS**

### Repeated calls

Repeated `get_server` calls completed without connection failures, progressive degradation, or inconsistent responses.

**PASS**

### Multiple clients

Multiple MCP clients connected independently and successfully executed tool calls.

**PASS**

### Concurrent writes

Multiple clients created alerts concurrently. Both writes were persisted and subsequently visible through `get_active_alerts` without locking failures, lost writes, corrupted results, or inconsistent counts.

**PASS**

## 12. LLM Integration

The MCP server was tested through `mcp-cmd.sh` using Groq and `openai/gpt-oss-120b`.

The larger model became the preferred validation baseline after `openai/gpt-oss-20b` encountered Groq free-tier token-per-minute limits when context grew too large.

A context budget was also introduced:

```text
MCP_MAX_CONTEXT_TOKENS=4000
```

The one-shot `cmd` workflow helps avoid unbounded conversational context growth.

## 13. Grounding Strategy

A global grounding instruction constrains operational answers to MCP-returned facts.

The intended behavior is to:

- use MCP tool data as the source of operational facts;
- avoid inventing server state;
- distinguish facts from interpretation;
- call additional tools when information is required;
- not infer that `online` means "no alerts".

## 14. Tool Semantics and LLM Composition

Individual tool correctness is not sufficient for an MCP intended for LLM use. The tools were tested through natural-language operational questions.

### Issue: `online` does not mean healthy

The model initially treated `status=online` as evidence that a server had no alerts.

This was corrected by strengthening the `get_server` semantics: server operational status and alert state are separate dimensions. `get_active_alerts` must be used when determining alert conditions.

### Issue: fleet-wide analysis

The model initially could not reliably answer questions such as:

> Which server has the highest CPU usage?

because it needed to discover and inspect multiple servers.

Fleet-wide discovery semantics were added to `search_servers`.

The model subsequently performed:

```text
search_servers
    ↓
get_server_metrics
    ↓
compare CPU values
```

and correctly identified the server with the highest observed CPU.

## 15. End-to-End Validation

A final realistic scenario was executed:

> Give me a health assessment of the production environment. Identify the most serious issue, the server with the highest CPU usage, and any other relevant warnings. Base the answer only on data returned by the MCP tools.

The model composed multiple MCP tools and produced a grounded assessment.

It correctly identified:

- `web-server-02` as the critical issue because of the connection-timeout alert;
- `db-server-01` as the highest observed CPU server at `83.2%`;
- the corresponding CPU warning on `db-server-01`;
- repeated CPU warnings on `web-server-01`;
- the informational maintenance alert as non-critical.

**Result: PASS**

## 16. Tool-Call Efficiency

The final end-to-end test showed some redundant `search_servers` calls. The answer was nevertheless correct and grounded.

This was deliberately not optimized in v1. Correctness and reliable composition take priority over minimizing calls.

Potential optimization is deferred to v2.

## 17. Structured Output

FastMCP generates output schemas from the Python return types. Current generic dictionary returns produce broad schemas such as:

```json
{
  "type": "object",
  "additionalProperties": true
}
```

Richer typed response models and explicit structured MCP content were investigated but deliberately deferred.

### Backlog

- Replace generic `dict[str, Any]` responses with typed models where useful.
- Investigate richer `structuredContent` handling.

## 18. Problems Fixed During v1

- Persistence/database IDs leaking into MCP-facing responses.
- Server lookup limited to internal identifiers.
- Missing IP-based lookup.
- Missing partial-name search behavior.
- Weak input schemas.
- Numeric constraints represented only in prose.
- Alert severity represented only as a free-form string.
- Ambiguous semantics around server status versus alerts.
- Insufficient fleet-wide discovery for cross-server reasoning.
- Alert creation persistence/object mismatch.
- Excessive LLM context growth during interactive sessions.
- Tool-composition issues revealed by realistic operational questions.

## 19. MCP v1 Acceptance Criteria

- [x] MCP server starts successfully.
- [x] MCP initialization succeeds.
- [x] Tools are discoverable through `tools/list`.
- [x] Six operational tools are exposed.
- [x] Persistence IDs are hidden from clients.
- [x] Server names can identify servers.
- [x] IP addresses can identify servers.
- [x] Partial server search works.
- [x] Fleet-wide discovery works.
- [x] Input schemas expose important constraints.
- [x] Runtime validation rejects invalid input.
- [x] Unknown servers produce clear errors.
- [x] Multiple MCP clients can connect.
- [x] Reconnect after restart works.
- [x] Repeated calls remain stable.
- [x] Concurrent alert writes work.
- [x] LLM tool selection works.
- [x] Multi-tool reasoning works.
- [x] Fleet-wide metric comparison works.
- [x] Alert correlation works.
- [x] Grounded production assessment works.

## 20. Deliberate Backlog

### Rich typed output schemas

Replace generic `dict[str, Any]` responses with typed response models where useful.

### Explicit structured MCP content

Investigate richer `structuredContent` handling instead of relying primarily on serialized JSON/text representation.

### Tool-call optimization

Reduce redundant searches and unnecessary calls made by the LLM.

### Additional operational tools

Do not add tools until a concrete use case demonstrates that the existing primitives cannot support it.

### Higher-load concurrency testing

The current concurrency tests establish basic correctness only. Dedicated stress testing can be added if production-scale concurrency guarantees are required.

## 21. v1 Status

**Server Hub MCP v1 — COMPLETE**

The current implementation has been validated at:

```text
protocol level
      ↓
tool level
      ↓
validation level
      ↓
lifecycle level
      ↓
concurrency level
      ↓
LLM tool-selection level
      ↓
multi-tool reasoning level
      ↓
end-to-end operational reasoning
```

This is a suitable checkpoint for a version tag such as:

```text
v1.0.0
```

## 22. Next Phase

The next development phase can return to the underlying REST/API layer while treating MCP v1 as a stable abstraction boundary.

Future MCP changes should preserve these principles:

1. Keep persistence details behind the MCP boundary.
2. Prefer meaningful identifiers over database IDs.
3. Make constraints explicit in schemas.
4. Make tool semantics unambiguous for LLMs.
5. Keep MCP responses concise and relevant.
6. Prefer a small set of composable tools over a large tool catalog.
7. Validate behavior through realistic LLM scenarios, not only direct unit tests.
