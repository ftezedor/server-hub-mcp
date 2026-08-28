# MCP Playground — v0.2

A browser-based MCP test client.

## v0.2 scope

This version adds the first real MCP capability:

1. Configure an OpenAI-compatible LLM endpoint.
2. Test the LLM connection.
3. Configure an MCP Streamable HTTP endpoint.
4. Establish an MCP session.
5. Initialize the MCP client.
6. Call `tools/list`.
7. Display the tools advertised by the server.

The LLM and MCP connections are intentionally independent.

## Running

```bash
npm install
npm run dev
```

Open the URL shown by Vite.

For the Server Hub MCP project, use:

```text
http://localhost:8000/mcp
```

## Important browser requirement

Because this is a browser client, the MCP server must allow the SPA origin through CORS. The LLM provider must also permit browser requests.

The API key remains in browser memory and is not persisted by this application.

## Next

v0.3 can connect the LLM and MCP together: advertise the discovered MCP tools to the LLM, process tool calls, execute them through MCP, and return the results to the LLM.
