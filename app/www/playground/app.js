const presets = {
  groq: { name: "Groq", baseUrl: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile" },
  openai: { name : "OpenAI", baseUrl: "https://api.openai.com/v1", model: "" },
  together: { name : "Together", baseUrl: "https://api.together.xyz/v1", model: "" },
  openrouter: { name : "OpenRouter", baseUrl: "https://openrouter.ai/api/v1", model: "minimax/minimax-m2.7:free" },
  ollama: { name : "Ollama", baseUrl: "http://localhost:11434/v1", model: "" },
  roteia: { name : "Roteia", baseUrl: "https://api.roteia.ai/v1", model: "minimax/minimax-m3:free" }
};

const $ = (id) => document.getElementById(id);
const logLines = [];

function log(message) {
  logLines.push(`[${new Date().toLocaleTimeString()}] ${message}`);
  $("log").textContent = logLines.join("\n");
}

// Add providers to the providers' dropdown
for (const [id, preset] of Object.entries(presets)) {
  $("provider").add(new Option(preset.name ?? id, id));
}

$("provider").addEventListener("change", () => {
  const preset = presets[$("provider").value];
  if (preset) {
    $("baseUrl").value = preset.baseUrl;
    $("model").value = preset.model;
  }
});

let mcpSessionId = null;

async function mcpRequest(url, body) {
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
  };

  if (mcpSessionId) {
    headers["Mcp-Session-Id"] = mcpSessionId;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body)
  });

  const sessionId = response.headers.get("Mcp-Session-Id");
  if (sessionId) {
    mcpSessionId = sessionId;
  }

  const contentType = response.headers.get("Content-Type") || "";
  const text = await response.text();

  if (!response.ok) {
    throw new Error(text || `HTTP ${response.status}`);
  }

  if (contentType.includes("text/event-stream")) {
    const dataLines = text
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .filter(Boolean);

    if (!dataLines.length) {
      throw new Error("MCP returned an empty event stream.");
    }

    return JSON.parse(dataLines[dataLines.length - 1]);
  }

  return text ? JSON.parse(text) : null;
}

$("mcpConnect").addEventListener("click", async () => {
  const url = $("mcpUrl").value.trim() || "/mcp";
  const status = $("mcpStatus");
  const button = $("mcpConnect");
  const toolsElement = $("tools");

  status.className = "status";
  status.textContent = "";
  button.disabled = true;
  toolsElement.innerHTML = "";
  mcpSessionId = null;

  try {
    log(`Connecting to MCP endpoint: ${url}`);

    const initialize = await mcpRequest(url, {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-06-18",
        capabilities: {},
        clientInfo: { name: "mcp-playground", version: "0.2.0" }
      }
    });

    if (initialize?.error) {
      throw new Error(initialize.error.message);
    }

    log("MCP initialize completed.");

    const result = await mcpRequest(url, {
      jsonrpc: "2.0",
      id: 2,
      method: "tools/list",
      params: {}
    });

    if (result?.error) {
      throw new Error(result.error.message);
    }

    const tools = result?.result?.tools || [];
    log(`tools/list returned ${tools.length} tool(s).`);

    $("toolCount").textContent = `(${tools.length})`;

    if (!tools.length) {
      toolsElement.innerHTML = "<p>No tools were advertised by this server.</p>";
    } else {
      for (const tool of tools) {
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
    }

    status.textContent = "Connected";
    status.classList.add("ok");
  } catch (error) {
    status.textContent = `Connection failed: ${error.message}`;
    status.classList.add("error");
    $("toolCount").textContent = "";
    toolsElement.innerHTML = "<p>Unable to discover tools.</p>";
    log(`MCP error: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

$("llmConnect").addEventListener("click", async () => {
  const url = $("baseUrl").value.trim().replace(/\/$/, "");
  const key = $("apiKey").value.trim();
  const model = $("model").value.trim();
  const status = $("llmStatus");
  const button = $("llmConnect");

  status.className = "status";

  if (!url || !model) {
    status.textContent = "Base URL and model are required.";
    status.classList.add("error");
    return;
  }

  button.disabled = true;
  status.textContent = "Testing LLM connection...";

  try {
    const headers = { 
      "Content-Type": "application/json",
      // "include_reasoning": "false",
      //"reasoning_effort": "none" 
    };
    if (key) headers.Authorization = `Bearer ${key}`;

    const response = await fetch(`${url}/chat/completions`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        model,
        messages: [
          {
            "role": "system",
            "content": "Answer directly and concisely. Do not include internal analysis. Do not include any instructions."
          },
          { 
            "role": "user", 
            "content": "Introduce yourself briefly by saying: I am [your model name]." 
          }
        ]
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data?.error?.message || `HTTP ${response.status}`);
    }

    const message = data?.choices?.[0]?.message?.content;
    if (!message) {
      throw new Error("The provider returned no assistant message.");
    }

    status.textContent = message;
    status.classList.add("ok");
  } catch (error) {
    status.textContent = `Connection failed: ${error.message}`;
    status.classList.add("error");
  } finally {
    button.disabled = false;
  }
});
