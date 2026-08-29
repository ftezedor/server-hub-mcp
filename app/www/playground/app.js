const presets = {
  groq: {
    name: "Groq",
    baseUrl: "https://api.groq.com/openai/v1",
    model: "llama-3.3-70b-versatile",
  },
  openai: { name: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "" },
  together: {
    name: "Together",
    baseUrl: "https://api.together.xyz/v1",
    model: "",
  },
  openrouter: {
    name: "OpenRouter",
    baseUrl: "https://openrouter.ai/api/v1",
    model: "minimax/minimax-m2.7:free",
  },
  ollama: { name: "Ollama", baseUrl: "http://localhost:11434/v1", model: "" },
  roteia: {
    name: "Roteia",
    baseUrl: "https://api.roteia.ai/v1",
    model: "minimax/minimax-m3:free",
  },
};
const $ = (id) => document.getElementById(id);
const logLines = [];
let mcpSessionId = null;
let mcpTools = [];
let llmConnected = false;

function updateExecutionSummary(execution) {
  const panel = $("executionSummary");
  if (!panel) return;

  $("summaryToolCount").textContent = String(execution.toolCount);
  $("summaryLlmTurns").textContent = String(execution.llmTurns);
  $("summaryOperations").textContent = String(execution.toolCount);
  $("summaryLlmTokens").textContent = execution.tokens.known
    ? execution.tokens.total.toLocaleString()
    : "—";

  const costElement = $("summaryLlmCost");
  if (costElement) {
    costElement.textContent = execution.tokens.costKnown
      ? `$${execution.tokens.cost.toFixed(4)}`
      : "—";
  }

  execution.durationMs = Date.now() - execution.startedAt;
  $("summaryDuration").textContent = `${execution.durationMs} ms`;

  const mcpMetrics = getMcpMetrics(execution);
  execution.mcp.metrics = mcpMetrics;

  const mcpPerformance = $("mcpPerformance");
  if (mcpPerformance && mcpMetrics.total > 0) {
    mcpPerformance.classList.remove("hidden");

    const total = $("summaryMcpTotal");
    const average = $("summaryMcpAverage");
    const fastest = $("summaryMcpFastest");
    const slowest = $("summaryMcpSlowest");

    if (total) total.textContent = `${mcpMetrics.total} ms`;
    if (average) average.textContent = `${mcpMetrics.average} ms`;
    if (fastest && mcpMetrics.fastest) {
      fastest.textContent = `${mcpMetrics.fastest.name} · ${mcpMetrics.fastest.duration} ms`;
    }
    if (slowest && mcpMetrics.slowest) {
      slowest.textContent = `${mcpMetrics.slowest.name} · ${mcpMetrics.slowest.duration} ms`;
    }
  }

  const exportButton = $("exportMarkdown");
  if (exportButton) {
    exportButton.hidden = false;
  }

  panel.classList.remove("hidden");
}

function addCommunicationStep(message, state = "active") {
  const log = $("communicationLog");
  log.classList.remove("hidden");
  const row = document.createElement("div");
  row.className = `communication-step ${state}`;
  row.innerHTML = `<span>${state === "done" ? "✓" : state === "error" ? "!" : "•"}</span><span>${escapeHtml(message)}</span>`;
  $("communicationSteps").appendChild(row);

  const execution = window.__mcpCurrentExecution;
  if (execution) {
    execution.communication.push({
      message,
      state,
      at: Date.now(),
    });
  }
}
function resetCommunicationLog() {
  $("communicationSteps").innerHTML = "";
  $("communicationLog").classList.remove("hidden");
}
function expandConfig(cardId, bodyId) {
  $(cardId).classList.remove("collapsed");
  $(bodyId).setAttribute("aria-hidden", "false");
}
function collapseConfig(cardId, bodyId) {
  $(cardId).classList.add("collapsed");
  $(bodyId).setAttribute("aria-hidden", "true");
}
function log(message) {
  logLines.push(`[${new Date().toLocaleTimeString()}] ${message}`);
  $("log").textContent = logLines.join("\n");
}
function setStatus(element, message, ok = false) {
  element.className = "status";
  element.textContent = message;
  if (ok) element.classList.add("ok");
  else if (message) element.classList.add("error");
}
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function inlineMarkdown(value) {
  let text = escapeHtml(value);
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return text;
}
function renderMarkdown(markdown) {
  const lines = String(markdown ?? "")
    .replace(/\r/g, "")
    .split("\n");
  const html = [];
  let paragraph = [];
  let table = [];
  const flushParagraph = () => {
    if (paragraph.length) {
      html.push(
        `<p>${inlineMarkdown(paragraph.join("\n")).replace(/\n/g, "<br>")}</p>`,
      );
      paragraph = [];
    }
  };
  const flushTable = () => {
    if (!table.length) return;
    const rows = table
      .map((line) =>
        line
          .split("|")
          .slice(1, -1)
          .map((cell) => cell.trim()),
      )
      .filter((row) => row.length);
    if (rows.length < 2 || !rows[1].every((cell) => /^:?-{3,}:?$/.test(cell))) {
      paragraph.push(...table);
      table = [];
      return;
    }
    let out = "<table><thead><tr>";
    rows[0].forEach((cell) => (out += `<th>${inlineMarkdown(cell)}</th>`));
    out += "</tr></thead><tbody>";
    rows.slice(2).forEach((row) => {
      out += "<tr>";
      for (let i = 0; i < rows[0].length; i++)
        out += `<td>${inlineMarkdown(row[i] ?? "")}</td>`;
      out += "</tr>";
    });
    html.push(out + "</tbody></table>");
    table = [];
  };
  for (const line of lines) {
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      flushParagraph();
      table.push(line.trim());
      continue;
    }
    flushTable();
    if (!line.trim()) {
      flushParagraph();
      continue;
    }
    if (/^#{1,3}\s/.test(line)) {
      flushParagraph();
      html.push(
        `<strong>${inlineMarkdown(line.replace(/^#{1,3}\s+/, ""))}</strong>`,
      );
      continue;
    }
    paragraph.push(line);
  }
  flushTable();
  flushParagraph();
  return html.join("");
}
function renderActivity(toolName, argumentsValue, result, duration) {
  const activity = $("activity");

  if (activity.querySelector("p")) {
    activity.innerHTML = "";
  }

  const item = document.createElement("div");
  item.className = "activity-item";

  const title = document.createElement("strong");
  title.textContent = `→ ${toolName}`;

  if (typeof duration === "number") {
    const durationLabel = document.createElement("span");
    durationLabel.className = "activity-duration";
    durationLabel.textContent = `${duration} ms`;
    title.appendChild(durationLabel);
  }

  const argsDetails = document.createElement("details");
  const argsSummary = document.createElement("summary");
  argsSummary.textContent = "Request";
  const args = document.createElement("pre");
  args.textContent = JSON.stringify(argumentsValue ?? {}, null, 2);
  argsDetails.append(argsSummary, args);

  const resultDetails = document.createElement("details");
  const resultSummary = document.createElement("summary");

  const isError =
    result &&
    typeof result === "object" &&
    Object.prototype.hasOwnProperty.call(result, "error");

  if (isError) {
    resultSummary.textContent = "Error";
    resultSummary.className = "activity-error-summary";
  } else {
    resultSummary.textContent = "Result";
  }

  const resultElement = document.createElement("pre");
  resultElement.textContent = JSON.stringify(result, null, 2);
  resultDetails.append(resultSummary, resultElement);

  item.append(title, argsDetails, resultDetails);
  activity.appendChild(item);
}

$("editLlm").addEventListener("click", () =>
  expandConfig("llmCard", "llmConfigBody"),
);
$("editMcp").addEventListener("click", () =>
  expandConfig("mcpCard", "mcpConfigBody"),
);

for (const [id, preset] of Object.entries(presets))
  $("provider").add(new Option(preset.name ?? id, id));
$("provider").addEventListener("change", () => {
  const preset = presets[$("provider").value];
  if (preset) {
    $("baseUrl").value = preset.baseUrl;
    $("model").value = preset.model;
  }
});
$("provider").dispatchEvent(new Event("change"));

async function mcpRequest(url, body) {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (mcpSessionId) headers["Mcp-Session-Id"] = mcpSessionId;
  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const sessionId = response.headers.get("Mcp-Session-Id");
  if (sessionId) mcpSessionId = sessionId;
  const contentType = response.headers.get("Content-Type") || "";
  const text = await response.text();
  if (!response.ok) throw new Error(text || `HTTP ${response.status}`);
  if (contentType.includes("text/event-stream")) {
    const dataLines = text
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .filter(Boolean);
    if (!dataLines.length)
      throw new Error("MCP returned an empty event stream.");
    return JSON.parse(dataLines[dataLines.length - 1]);
  }
  return text ? JSON.parse(text) : null;
}
async function connectMcp() {
  const url = $("mcpUrl").value.trim() || "/mcp";
  const status = $("mcpStatus");
  const button = $("mcpConnect");
  button.disabled = true;
  setStatus(status, "");
  mcpSessionId = null;
  mcpTools = [];
  try {
    log(`Connecting to MCP endpoint: ${url}`);
    const initialize = await mcpRequest(url, {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-06-18",
        capabilities: {},
        clientInfo: { name: "mcp-playground", version: "0.4.0" },
      },
    });
    if (initialize?.error) throw new Error(initialize.error.message);
    log("MCP initialize completed.");
    const result = await mcpRequest(url, {
      jsonrpc: "2.0",
      id: 2,
      method: "tools/list",
      params: {},
    });
    if (result?.error) throw new Error(result.error.message);
    mcpTools = result?.result?.tools || [];
    log(`tools/list returned ${mcpTools.length} tool(s).`);
    $("toolCount").textContent = mcpTools.length;
    $("mcpToolsSummary").textContent = mcpTools.length;
    $("toolCountBadge").textContent = mcpTools.length;
    const toolsElement = $("tools");
    toolsElement.innerHTML = "";
    if (!mcpTools.length)
      toolsElement.innerHTML =
        "<p>No tools were advertised by this server.</p>";
    else
      for (const tool of mcpTools) {
        const element = document.createElement("div");
        element.className = "tool";
        const name = document.createElement("strong");
        name.textContent = tool.name;
        const description = document.createElement("small");
        description.textContent =
          tool.description || "No description provided.";
        element.append(name, description);
        toolsElement.appendChild(element);
      }
    setStatus(status, "Connected", true);
    $("mcpCard").classList.add("connected");
    collapseConfig("mcpCard", "mcpConfigBody");
    $("ask").disabled = !llmConnected;
  } catch (error) {
    setStatus(status, `Connection failed: ${error.message}`);
    $("toolCount").textContent = "0";
    $("mcpToolsSummary").textContent = "0";
    $("toolCountBadge").textContent = "0";
    $("mcpCard").classList.remove("connected");
    $("tools").innerHTML = "<p>Unable to discover tools.</p>";
    log(`MCP error: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}
$("mcpConnect").addEventListener("click", connectMcp);

async function connectLlm() {
  const url = $("baseUrl").value.trim().replace(/\/$/, "");
  const key = $("apiKey").value.trim();
  const model = $("model").value.trim();
  const status = $("llmStatus");
  const button = $("llmConnect");
  setStatus(status, "");
  if (!url || !model) {
    setStatus(status, "Base URL and model are required.");
    return;
  }
  button.disabled = true;
  status.className = "status";
  status.textContent = "Testing LLM connection...";
  try {
    const headers = { "Content-Type": "application/json" };
    if (key) headers.Authorization = `Bearer ${key}`;
    const response = await fetch(`${url}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model,
        messages: [
          {
            role: "system",
            content:
              "Answer directly and concisely. Do not include internal analysis.",
          },
          {
            role: "user",
            content:
              "Introduce yourself briefly by saying: I am [your model name].",
          },
        ],
      }),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(data?.error?.message || `HTTP ${response.status}`);
    const message = data?.choices?.[0]?.message?.content;
    if (!message)
      throw new Error("The provider returned no assistant message.");
    status.textContent = message;
    status.classList.add("ok");
    llmConnected = true;
    $("llmModelSummary").textContent = model;
    $("llmCard").classList.add("connected");
    collapseConfig("llmCard", "llmConfigBody");
    $("ask").disabled = mcpTools.length === 0;
  } catch (error) {
    llmConnected = false;
    $("llmCard").classList.remove("connected");
    $("llmModelSummary").textContent = "Not connected";
    $("ask").disabled = true;
    setStatus(status, `Connection failed: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}
$("llmConnect").addEventListener("click", connectLlm);

function toOpenAiTools(tools) {
  return tools.map((tool) => ({
    type: "function",
    function: {
      name: tool.name,
      description: tool.description || "",
      parameters: tool.inputSchema || { type: "object", properties: {} },
    },
  }));
}

async function callLlm(messages, tools) {
  const url = $("baseUrl").value.trim().replace(/\/$/, "");
  const key = $("apiKey").value.trim();
  const model = $("model").value.trim();
  const headers = { "Content-Type": "application/json" };
  if (key) headers.Authorization = `Bearer ${key}`;
  const body = { model, messages };
  if (tools.length) body.tools = toOpenAiTools(tools);
  const response = await fetch(`${url}/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data?.error?.message || `HTTP ${response.status}`);
  const message = data?.choices?.[0]?.message;
  if (!message) throw new Error("The provider returned no assistant message.");
  return {
    message,
    usage: data?.usage || null,
    cost: extractLlmCost(data),
  };
}

function extractLlmCost(data) {
  const candidates = [
    data?.usage?.cost,
    data?.usage?.total_cost,
    data?.usage?.totalCost,
    data?.cost,
    data?.total_cost,
    data?.totalCost,
  ];

  for (const value of candidates) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    if (typeof value === "string" && value.trim() !== "") {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return null;
}

function normalizeTokenUsage(usage) {
  if (!usage || typeof usage !== "object") {
    return {
      prompt: null,
      completion: null,
      reasoning: null,
      total: null,
      known: false,
    };
  }

  const prompt =
    usage.prompt_tokens ??
    usage.input_tokens ??
    usage.promptTokens ??
    usage.inputTokens ??
    null;

  const completion =
    usage.completion_tokens ??
    usage.output_tokens ??
    usage.completionTokens ??
    usage.outputTokens ??
    null;

  const reasoning =
    usage.completion_tokens_details?.reasoning_tokens ??
    usage.output_tokens_details?.reasoning_tokens ??
    usage.reasoning_tokens ??
    usage.reasoningTokens ??
    null;

  const total =
    usage.total_tokens ??
    usage.totalTokens ??
    (typeof prompt === "number" && typeof completion === "number"
      ? prompt + completion
      : null);

  return {
    prompt,
    completion,
    reasoning,
    total,
    known: typeof total === "number",
  };
}

async function callMcpTool(toolName, argumentsValue) {
  const url = $("mcpUrl").value.trim() || "/mcp";
  const result = await mcpRequest(url, {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "tools/call",
    params: { name: toolName, arguments: argumentsValue || {} },
  });
  if (result?.error) throw new Error(result.error.message);
  return result?.result;
}

function getMcpMetrics(execution) {
  const tools = execution.mcp.toolCalls.filter(
    (tool) => typeof tool.duration === "number",
  );

  if (!tools.length) {
    return {
      total: 0,
      average: 0,
      fastest: null,
      slowest: null,
    };
  }

  const total = tools.reduce((sum, tool) => sum + tool.duration, 0);
  const fastest = tools.reduce((best, tool) =>
    tool.duration < best.duration ? tool : best,
  );
  const slowest = tools.reduce((worst, tool) =>
    tool.duration > worst.duration ? tool : worst,
  );

  return {
    total,
    average: Math.round(total / tools.length),
    fastest,
    slowest,
  };
}

function generateExecutionMarkdown(execution) {
  const lines = [];

  const formatJson = (value) => {
    try {
      return JSON.stringify(value ?? {}, null, 2);
    } catch {
      return String(value);
    }
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return "—";
    return new Date(timestamp).toISOString();
  };

  const formatCost = () => {
    if (!execution.tokens.costKnown) return "—";
    return `$${execution.tokens.cost.toFixed(4)}`;
  };

  lines.push("# MCP Playground Execution");
  lines.push("");
  lines.push(`**Export timestamp:** ${formatDate(Date.now())}`);
  lines.push("");

  lines.push("## Execution Summary");
  lines.push("");
  lines.push("| Metric | Value |");
  lines.push("| --- | ---: |");
  lines.push(`| Started | ${formatDate(execution.metadata.startedAt)} |`);
  lines.push(`| Completed | ${formatDate(execution.metadata.completedAt)} |`);
  lines.push(`| Duration | ${execution.durationMs} ms |`);
  lines.push(`| LLM turns | ${execution.llmTurns} |`);
  lines.push(`| MCP tool calls | ${execution.toolCount} |`);
  lines.push(
    `| LLM tokens | ${
      execution.tokens.known ? execution.tokens.total.toLocaleString() : "—"
    } |`,
  );
  lines.push(`| LLM cost | ${formatCost()} |`);
  lines.push("");

  lines.push("## Question");
  lines.push("");
  lines.push(execution.request.prompt || "—");
  lines.push("");

  lines.push("## LLM");
  lines.push("");
  lines.push(`- **Provider:** ${execution.llm.provider || "—"}`);
  lines.push(`- **Model:** ${execution.llm.model || "—"}`);
  lines.push(`- **Base URL:** ${execution.llm.baseUrl || "—"}`);
  lines.push(`- **Turns:** ${execution.llm.turns}`);
  lines.push("");

  lines.push("## MCP Performance");
  lines.push("");

  const metrics = execution.mcp.metrics;

  if (metrics && metrics.total > 0) {
    lines.push("| Metric | Value |");
    lines.push("| --- | ---: |");
    lines.push(`| Total MCP time | ${metrics.total} ms |`);
    lines.push(`| Average | ${metrics.average} ms |`);
    lines.push(
      `| Fastest | ${
        metrics.fastest
          ? `${metrics.fastest.name} · ${metrics.fastest.duration} ms`
          : "—"
      } |`,
    );
    lines.push(
      `| Slowest | ${
        metrics.slowest
          ? `${metrics.slowest.name} · ${metrics.slowest.duration} ms`
          : "—"
      } |`,
    );
  } else {
    lines.push("No MCP tool calls were recorded.");
  }

  lines.push("");

  lines.push("## Communication Log");
  lines.push("");

  if (execution.communication.length) {
    execution.communication.forEach((entry, index) => {
      lines.push(
        `${index + 1}. **${entry.state || "info"}** — ${entry.message}`,
      );
    });
  } else {
    lines.push("No communication events were recorded.");
  }

  lines.push("");

  lines.push("## MCP Activity");
  lines.push("");

  if (execution.mcp.toolCalls.length) {
    execution.mcp.toolCalls.forEach((tool, index) => {
      lines.push(`### ${index + 1}. ${tool.name}`);
      lines.push("");
      lines.push(`- **Duration:** ${tool.duration} ms`);
      lines.push(`- **Status:** ${tool.success ? "Success" : "Failed"}`);
      lines.push("");

      lines.push("#### Request");
      lines.push("");
      lines.push("```json");
      lines.push(formatJson(tool.arguments));
      lines.push("```");
      lines.push("");

      if (tool.success) {
        lines.push("#### Result");
        lines.push("");
        lines.push("```json");
        lines.push(formatJson(tool.result));
        lines.push("```");
      } else {
        lines.push("#### Error");
        lines.push("");
        lines.push("```text");
        lines.push(tool.error || "Unknown error");
        lines.push("```");
      }

      lines.push("");
    });
  } else {
    lines.push("No MCP activity was recorded.");
    lines.push("");
  }

  lines.push("## Final Answer");
  lines.push("");
  lines.push(execution.answer || "—");
  lines.push("");

  return lines.join("\n");
}

$("exportMarkdown")?.addEventListener("click", () => {
  const execution = window.__mcpCurrentExecution;

  if (!execution) {
    return;
  }

  const markdown = generateExecutionMarkdown(execution);

  const blob = new Blob([markdown], {
    type: "text/markdown;charset=utf-8",
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");

  link.href = url;
  link.download = `mcp-playground-${timestamp}.md`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
});

$("ask").addEventListener("click", async () => {
  const prompt = $("prompt").value.trim();
  const answer = $("answer");
  const button = $("ask");
  if (!prompt) {
    answer.textContent = "Enter a question first.";
    answer.classList.add("error");
    return;
  }
  if (!llmConnected) {
    answer.textContent = "Connect the LLM first.";
    answer.classList.add("error");
    return;
  }
  if (!mcpTools.length) {
    answer.textContent = "Connect to MCP and discover its tools first.";
    answer.classList.add("error");
    return;
  }
  button.disabled = true;
  $("answerPanel").classList.remove("hidden");
  answer.className = "answer";
  answer.textContent = "Thinking…";
  $("activity").innerHTML = "<p>Waiting for tool activity...</p>";
  resetCommunicationLog();
  addCommunicationStep("Asking LLM");
  $("executionSummary").classList.add("hidden");
  $("mcpPerformance").classList.add("hidden");
  $("exportMarkdown").hidden = true;
  try {
    const messages = [
      {
        role: "system",
        content: [
          "You are using the Server Hub MCP server.",
          "Use an MCP tool when it is needed to answer the user's question.",
          "After receiving a tool result, answer the user directly and concisely.",
          "Present results clearly for a human reader.",
          "When the result contains tabular data, format it as a properly aligned Markdown table.",
          "Use short paragraphs and bullet lists when appropriate.",
          "Do not expose raw JSON, internal tool calls, or internal reasoning unless explicitly requested.",
        ].join(" "),
      },
      { role: "user", content: prompt },
    ];
    log(`LLM request with ${mcpTools.length} MCP tool(s).`);
    const execution = {
      metadata: {
        startedAt: Date.now(),
        completedAt: null,
        durationMs: 0,
      },
      request: {
        prompt,
      },
      llm: {
        provider: $("provider").value,
        baseUrl: $("baseUrl").value.trim(),
        model: $("model").value.trim(),
        turns: 0,
      },
      mcp: {
        endpoint: $("mcpUrl").value.trim() || "/mcp",
        toolCalls: [],
        metrics: null,
      },
      toolCount: 0,
      llmTurns: 0,
      startedAt: 0,
      durationMs: 0,
      tokens: {
        prompt: 0,
        completion: 0,
        reasoning: 0,
        total: 0,
        known: false,
        cost: 0,
        costKnown: false,
      },
      communication: [],
      answer: "",
    };

    execution.startedAt = execution.metadata.startedAt;
    window.__mcpCurrentExecution = execution;

    const maxToolRounds = 12;
    let round = 0;
    while (round < maxToolRounds) {
      round += 1;
      const llmStartedAt = Date.now();
      const llmResponse = await callLlm(messages, mcpTools);
      const llmDuration = Date.now() - llmStartedAt;
      execution.llmTurns += 1;
      execution.llm.turns = execution.llmTurns;

      const assistantMessage = llmResponse.message;
      const usage = normalizeTokenUsage(llmResponse.usage);

      let tokenInfo = "tokens unavailable";

      if (usage.known) {
        execution.tokens.prompt += usage.prompt ?? 0;
        execution.tokens.completion += usage.completion ?? 0;
        execution.tokens.total += usage.total;
        execution.tokens.known = true;

        tokenInfo = `${usage.total.toLocaleString()} tokens`;
      }

      if (
        typeof llmResponse.cost === "number" &&
        Number.isFinite(llmResponse.cost) &&
        llmResponse.cost > 0
      ) {
        execution.tokens.cost += llmResponse.cost;
        execution.tokens.costKnown = true;
      }

      const toolCalls = assistantMessage.tool_calls || [];
      if (!toolCalls.length) {
        addCommunicationStep(
          `LLM response received · ${llmDuration} ms · ${tokenInfo}`,
          "done",
        );
        $("answerPanel").classList.remove("hidden");
        execution.answer =
          assistantMessage.content || "The model returned no final answer.";
        answer.innerHTML = renderMarkdown(execution.answer);
        execution.answer =
          assistantMessage.content || "The model returned no final answer.";
        execution.metadata.completedAt = Date.now();
        execution.durationMs =
          execution.metadata.completedAt - execution.startedAt;
        updateExecutionSummary(execution);
        addCommunicationStep("Final LLM response received", "done");
        log("Final LLM response received.");
        return;
      }
      addCommunicationStep(
        `LLM response received · ${llmDuration} ms · ${tokenInfo}`,
        "done",
      );
      messages.push(assistantMessage);
      for (const toolCall of toolCalls) {
        const toolName = toolCall.function?.name;
        if (!toolName)
          throw new Error("LLM returned a tool call without a function name.");
        let argumentsValue = {};
        try {
          argumentsValue = JSON.parse(toolCall.function?.arguments || "{}");
        } catch {
          throw new Error(`Invalid arguments returned for ${toolName}.`);
        }
        execution.toolCount += 1;
        addCommunicationStep(`LLM requested tool calling ${toolName}`);
        log(`LLM requested MCP tool: ${toolName}`);
        const toolStartedAt = Date.now();
        let toolResult;

        try {
          toolResult = await callMcpTool(toolName, argumentsValue);
          const toolDuration = Date.now() - toolStartedAt;

          execution.mcp.toolCalls.push({
            name: toolName,
            duration: toolDuration,
            success: true,
            arguments: argumentsValue,
            result: toolResult,
          });

          addCommunicationStep(
            `Tool calling response received · ${toolDuration} ms`,
            "done",
          );
          renderActivity(toolName, argumentsValue, toolResult, toolDuration);
        } catch (toolError) {
          const toolDuration = Date.now() - toolStartedAt;

          execution.mcp.toolCalls.push({
            name: toolName,
            duration: toolDuration,
            success: false,
            arguments: argumentsValue,
            error: toolError.message,
          });

          addCommunicationStep(
            `${toolName} failed · ${toolDuration} ms`,
            "error",
          );
          log(`MCP tool error (${toolName}): ${toolError.message}`);

          renderActivity(
            toolName,
            argumentsValue,
            { error: toolError.message },
            toolDuration,
          );

          throw toolError;
        }
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify(toolResult),
        });
        addCommunicationStep("Informing LLM");
      }
    }
    throw new Error(`Maximum MCP tool rounds (${maxToolRounds}) exceeded.`);
  } catch (error) {
    execution.metadata.completedAt = Date.now();
    execution.durationMs = execution.metadata.completedAt - execution.startedAt;
    addCommunicationStep(error.message, "error");
    $("answerPanel").classList.remove("hidden");
    answer.textContent = `Error: ${error.message}`;
    answer.className = "answer error";
    log(`Orchestration error: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

document.addEventListener("click", (event) => {
  const button = event.target.closest(".example-button");
  if (!button) return;
  const field = $("prompt");
  if (!field) return;
  field.value = button.dataset.prompt || "";
  field.focus();
  field.dispatchEvent(new Event("input", { bubbles: true }));
});
