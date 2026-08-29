# MCP Playground v0.7.7

MCP Playground is a lightweight browser-based interface for exploring interactions between a Large Language Model (LLM) and tools exposed through the Model Context Protocol (MCP).

The Playground is intentionally small and focused on the complete orchestration flow:

**User → LLM → MCP tool(s) → LLM → User**

It provides both a conversational view of the result and an execution-oriented view of what happened during the run.

---

## Features

### LLM connection

- Supports configurable OpenAI-compatible chat completion endpoints.
- Built-in provider presets for:
  - Groq
  - OpenAI
  - Together
  - OpenRouter
  - Ollama
  - Roteia
- Configurable base URL, API key, and model.
- LLM configuration collapses after a successful connection.
- The connected model remains visible while the configuration is collapsed.

### MCP connection

- Connects to an MCP endpoint using the Streamable HTTP-style request flow implemented by the Playground.
- Initializes an MCP session and discovers available tools.
- Displays discovered tools in the UI.
- MCP configuration collapses after a successful connection.
- The discovered tool count remains visible while collapsed.

### Iterative LLM ↔ MCP orchestration

The Playground supports iterative tool calling rather than a single tool invocation.

For each LLM turn:

1. The current conversation is sent to the configured LLM.
2. Discovered MCP tools are supplied as OpenAI-compatible function definitions.
3. If the LLM requests one or more tools, the Playground executes them through MCP.
4. Each tool result is returned to the LLM with its matching `tool_call_id`.
5. The process continues until the LLM produces a final answer.

A maximum of **12 MCP tool rounds** is enforced to prevent an unbounded orchestration loop.

### Communication trace

The Playground displays a live communication trace during execution, including events such as:

- Asking the LLM
- LLM responses
- LLM tool requests
- MCP tool responses
- MCP failures
- Informing the LLM
- Final LLM response

LLM responses and MCP tool executions include measured elapsed time.

### MCP activity trace

Every MCP tool execution is displayed with:

- Tool name
- Duration
- Request arguments
- Result payload
- Error information when the call fails

Request and result payloads are expandable to keep the interface compact.

### Execution summary

After an execution completes, the Playground displays an execution summary containing:

- MCP tools called
- LLM turns
- MCP operations
- LLM token usage, when supplied by the provider
- LLM cost, when supplied by the provider
- Total execution duration

### MCP performance

When MCP calls are recorded, the Playground calculates:

- Total MCP execution time
- Average MCP tool duration
- Fastest MCP call
- Slowest MCP call

These metrics are derived from the measured duration of the individual MCP tool calls.

### LLM token and cost tracking

The Playground normalizes common provider usage formats, including prompt/input, completion/output, reasoning, and total token counts.

Token totals are displayed only when usable token information is supplied by the provider.

LLM cost is tracked when the provider response exposes a usable cost value. The Playground does **not** estimate cost when the provider does not provide one.

### Example prompts

The Playground includes predefined prompts for common MCP/server investigation scenarios, including:

- Production review
- Production attention
- Critical alerts
- Performance hotspots
- CPU trends
- Memory pressure
- Correlating alerts with metrics
- System overview
- Server health
- Server comparison

These prompts populate the main question field without requiring the user to type the question manually.

### Markdown rendering

Assistant responses are rendered as lightweight Markdown in the browser.

The renderer supports the subset needed by the Playground, including:

- Paragraphs
- Line breaks
- Bold text
- Inline code
- Markdown tables
- Basic heading levels

The application does not depend on a third-party Markdown rendering library.

### Execution export

Completed executions can be exported through the floating **Export Run** button.

The export produces a Markdown report containing:

- Export timestamp
- Execution summary
- Original question
- LLM provider and model information
- MCP performance metrics
- Communication log
- MCP activity for every tool call
- Request arguments
- Tool results or errors
- Final answer

The generated file uses a timestamped filename such as:

```text
mcp-playground-2026-08-29T14-30-41-865Z.md
```

The export button remains fixed relative to the centered Playground layout while the page is scrolled and is hidden until an execution is available for export.

---

## User interface

The interface is organized into four main areas:

### 1. Connection configuration

Two cards configure the LLM and MCP connections.

### 2. Playground

The main interaction area contains:

- Predefined questions
- Prompt input
- Ask button
- Live LLM communication trace
- Assistant response
- Execution summary
- MCP performance metrics

### 3. MCP tools and activity

The lower section shows:

- Discovered MCP tools
- MCP execution activity

### 4. Debug log

The collapsible protocol log exposes diagnostic messages generated by the client.

---

## Execution lifecycle

A new execution starts when the user clicks **Ask**.

Before starting the new run, execution-specific UI is reset:

- Previous execution summary is hidden.
- Previous MCP performance metrics are hidden.
- The Export Run button is hidden.
- The communication trace is reset.
- Previous MCP activity is cleared.

A new execution object is then created and stored as the current execution state.

When the final LLM response is received:

- The answer is rendered.
- Execution completion time is recorded.
- Total duration is calculated.
- MCP performance metrics are calculated.
- The execution summary is displayed.
- The Export Run button becomes available.

The same execution object is used as the source for the Markdown export.

---

## Execution state

Each run is represented by a single execution object containing the information needed by the UI and export functionality.

Its main areas are:

```text
execution
├── metadata
│   ├── startedAt
│   ├── completedAt
│   └── durationMs
├── request
│   └── prompt
├── llm
│   ├── provider
│   ├── baseUrl
│   ├── model
│   └── turns
├── mcp
│   ├── endpoint
│   ├── toolCalls[]
│   └── metrics
├── toolCount
├── llmTurns
├── startedAt
├── durationMs
├── tokens
│   ├── prompt
│   ├── completion
│   ├── reasoning
│   ├── total
│   ├── known
│   ├── cost
│   └── costKnown
├── communication[]
└── answer
```

This state is kept as the single source of information for the current execution and is also exposed as `window.__mcpCurrentExecution` for the export action.

---

## MCP protocol flow

The client performs the following high-level MCP operations when connecting:

1. `initialize`
2. `notifications/initialized`
3. `tools/list`

Tool execution uses:

```text
POST /mcp
method: tools/call
```

with the selected tool name and its arguments.

The exact MCP endpoint is configurable through the MCP URL field and defaults to:

```text
/mcp
```

---

## LLM integration

The Playground uses an OpenAI-compatible `/chat/completions` interface.

The request contains:

- Model
- Conversation messages
- MCP tools converted to OpenAI-compatible function definitions

When tools are available, the request includes the discovered MCP tools in the `tools` field.

The Playground expects the provider to return an assistant message and optionally usage/cost information.

---

## Error handling

Errors are surfaced in several places depending on where they occur:

- LLM connection status
- MCP connection status
- Communication trace
- MCP activity trace
- Assistant response area
- Debug protocol log

Failed MCP tool calls are preserved in the execution state with their duration, arguments, and error message. This allows failed executions to remain useful for diagnosis and export.

---

## Project structure

```text
playground/
├── index.html
├── style.css
├── app.js
└── README.md
```

### `index.html`

Defines the Playground structure and UI components.

### `style.css`

Contains the complete visual design, responsive layout, execution panels, MCP activity styling, and floating Export Run control.

### `app.js`

Contains the client-side orchestration logic, including:

- LLM connection
- MCP connection
- Tool discovery
- Iterative LLM/MCP execution
- Token and cost normalization
- Execution metrics
- Communication tracing
- Markdown rendering
- Markdown export

---

## Running the Playground

The Playground is intended to be served as a static browser application by the surrounding MCP Playground/Server Hub application.

The HTML references:

```html
<link rel="stylesheet" href="/playground/style.css" />
<script src="/playground/app.js"></script>
```

The default MCP endpoint is:

```text
/mcp
```

An LLM-compatible endpoint and credentials must be configured through the UI before asking questions.

---

## Design principles

The Playground deliberately favors a small client-side implementation over a large framework.

The main principles are:

- Keep the LLM → MCP → LLM orchestration visible.
- Keep execution state centralized.
- Prefer measured values over estimates.
- Preserve MCP failures as part of the execution record.
- Keep configuration separate from execution results.
- Keep the UI compact while exposing detailed trace information when needed.
- Make completed executions reproducible as Markdown reports.

---

## Current version

**v0.7.7**

The version shown in the Playground header and footer is maintained in `index.html`.
