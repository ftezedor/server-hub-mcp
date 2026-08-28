# MCP Playground v0.4

v0.4 keeps the LLM → MCP → LLM flow from v0.3 and improves presentation.

- Modern responsive UI with connection indicators.
- Separate LLM and MCP configuration cards.
- Cleaner prompt/assistant experience.
- MCP tools displayed as compact cards.
- MCP calls displayed as a trace with arguments and results.
- Collapsible protocol log.
- Lightweight client-side Markdown rendering, including Markdown tables.
- Stronger system guidance asking the LLM to present tool results clearly and use tables for tabular data.

The orchestration model remains intentionally small: one LLM tool call followed by one final LLM response.


## v0.5 UX

- LLM and MCP configuration cards can be collapsed.
- Collapsed cards show the connected model name and discovered MCP tool count.
- The Ask workflow displays a live communication trace directly below the prompt.
- The v0.4 visual design remains the baseline.


## v0.5.1

- Fixed the assistant response panel: it is now made visible when Ask is clicked.
- The final LLM response is rendered below the communication trace using the
  existing Markdown/table renderer.


## v0.5.2

- Fixed the assistant response visibility bug: the final LLM response is now
  explicitly revealed when Ask starts and when the final response arrives.
- Added the Playground version to the top-right corner.
- LLM configuration automatically collapses after a successful connection.
- MCP configuration automatically collapses after a successful connection.
- Collapsed cards expose an Edit button so configuration can be changed later.
- The connected model name and MCP tool count remain visible while collapsed.


## v0.5.3

- Replaced the text-based Hide/Edit controls with a compact chevron disclosure
  control.
- The control changes direction when the card is collapsed or expanded.
- Added accessible `aria-label` and tooltip text for the control.


## v0.5.4 UX

- Expanded LLM/MCP cards no longer display a collapse button.
- Collapsed cards expose only a small, discrete Edit action.
- The Playground version is displayed immediately after the product name in
  the top-left header.


## v0.5.4 UI fix

- Corrected an extra closing `div` in the configuration grid markup.
- This restores the Playground and lower sections to the centered `.shell`
  layout instead of allowing the Playground card to span the viewport.
- Footer version is now consistent with the header (`v0.5.4`).


## v0.6.0 MCP orchestration

- MCP tool calling is now iterative instead of one-shot.
- Every LLM turn receives the discovered MCP tool definitions.
- Tool results are returned with their matching `tool_call_id`.
- Multiple sequential tool calls are supported, up to 12 rounds.
- The communication trace records each tool request, response, and LLM turn.


## v0.7.0 Playground demo UX

- Added one-click example prompts for server health, server comparison, and
  production-server attention analysis.
- Added a compact MCP execution summary showing tools called, LLM turns,
  MCP operations, and total elapsed time.
- Added timing to LLM and MCP tool-call trace entries.


## v0.7.1 fixes

- Corrected the visible Playground version to v0.7.1.
- Fixed one-click example prompt handlers.
- Added delegated click handling so example buttons remain functional if
  their surrounding DOM is rebuilt.


## v0.7.2 trace timing

- Shows measured elapsed time for every LLM response.
- Shows measured elapsed time for every MCP tool execution.
- Keeps orchestration markers untimed to avoid misleading measurements.
- Keeps the execution summary's total wall-clock duration.


## v0.7.3 fix

- Fixed the orchestration timing counters so they are initialized in the
  correct request scope.
- LLM and MCP operation durations are now displayed reliably.
- Execution summary is updated after the final LLM response.
