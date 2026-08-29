const presets = {
  groq: { name: "Groq", baseUrl: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile" },
  openai: { name: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "" },
  together: { name: "Together", baseUrl: "https://api.together.xyz/v1", model: "" },
  openrouter: { name: "OpenRouter", baseUrl: "https://openrouter.ai/api/v1", model: "minimax/minimax-m2.7:free" },
  ollama: { name: "Ollama", baseUrl: "http://localhost:11434/v1", model: "" },
  roteia: { name: "Roteia", baseUrl: "https://api.roteia.ai/v1", model: "minimax/minimax-m3:free" }
};
const $ = (id) => document.getElementById(id);
const logLines = [];
let mcpSessionId = null;
let mcpTools = [];
let llmConnected = false;

function updateExecutionSummary(toolCount, llmTurns, startedAt, tokenUsage) {
  const panel = $("executionSummary");
  if (!panel) return;
  $("summaryToolCount").textContent = String(toolCount);
  $("summaryLlmTurns").textContent = String(llmTurns);
  $("summaryOperations").textContent = String(toolCount);
  $("summaryLlmTokens").textContent = tokenUsage?.known ? tokenUsage.total.toLocaleString() : "—";
  $("summaryDuration").textContent = `${Date.now() - startedAt} ms`;
  panel.classList.remove("hidden");
}

function addCommunicationStep(message, state = "active") {
  const log = $("communicationLog");
  log.classList.remove("hidden");
  const row = document.createElement("div");
  row.className = `communication-step ${state}`;
  row.innerHTML = `<span>${state === "done" ? "✓" : state === "error" ? "!" : "•"}</span><span>${escapeHtml(message)}</span>`;
  $("communicationSteps").appendChild(row);
}
function resetCommunicationLog() { $("communicationSteps").innerHTML = ""; $("communicationLog").classList.remove("hidden"); }
function expandConfig(cardId, bodyId) { $(cardId).classList.remove("collapsed"); $(bodyId).setAttribute("aria-hidden", "false"); }
function collapseConfig(cardId, bodyId) { $(cardId).classList.add("collapsed"); $(bodyId).setAttribute("aria-hidden", "true"); }
function log(message) { logLines.push(`[${new Date().toLocaleTimeString()}] ${message}`); $("log").textContent = logLines.join("\n"); }
function setStatus(element, message, ok = false) { element.className = "status"; element.textContent = message; if (ok) element.classList.add("ok"); else if (message) element.classList.add("error"); }
function escapeHtml(value) { return String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;"); }

function inlineMarkdown(value) {
  let text = escapeHtml(value);
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  return text;
}
function renderMarkdown(markdown) {
  const lines = String(markdown ?? "").replace(/\r/g,"").split("\n");
  const html=[]; let paragraph=[]; let table=[];
  const flushParagraph=()=>{if(paragraph.length){html.push(`<p>${inlineMarkdown(paragraph.join("\n")).replace(/\n/g,"<br>")}</p>`);paragraph=[];}};
  const flushTable=()=>{if(!table.length)return;const rows=table.map(line=>line.split("|").slice(1,-1).map(cell=>cell.trim())).filter(row=>row.length);if(rows.length<2||!rows[1].every(cell=>/^:?-{3,}:?$/.test(cell))){paragraph.push(...table);table=[];return;}let out="<table><thead><tr>";rows[0].forEach(cell=>out+=`<th>${inlineMarkdown(cell)}</th>`);out+="</tr></thead><tbody>";rows.slice(2).forEach(row=>{out+="<tr>";for(let i=0;i<rows[0].length;i++)out+=`<td>${inlineMarkdown(row[i]??"")}</td>`;out+="</tr>";});html.push(out+"</tbody></table>");table=[];};
  for(const line of lines){if(line.trim().startsWith("|")&&line.trim().endsWith("|")){flushParagraph();table.push(line.trim());continue;}flushTable();if(!line.trim()){flushParagraph();continue;}if(/^#{1,3}\s/.test(line)){flushParagraph();html.push(`<strong>${inlineMarkdown(line.replace(/^#{1,3}\s+/,""))}</strong>`);continue;}paragraph.push(line);}
  flushTable();flushParagraph();return html.join("");
}
function renderActivity(toolName, argumentsValue, result) {
  const activity=$("activity"); if(activity.querySelector("p"))activity.innerHTML="";
  const item=document.createElement("div");item.className="activity-item";
  const title=document.createElement("strong");title.textContent=`→ ${toolName}`;
  const args=document.createElement("pre");args.textContent=JSON.stringify(argumentsValue??{},null,2);
  const resultTitle=document.createElement("strong");resultTitle.textContent="← Result";
  const resultElement=document.createElement("pre");resultElement.textContent=JSON.stringify(result,null,2);
  item.append(title,args,resultTitle,resultElement);activity.appendChild(item);
}

$("editLlm").addEventListener("click",()=>expandConfig("llmCard","llmConfigBody"));
$("editMcp").addEventListener("click",()=>expandConfig("mcpCard","mcpConfigBody"));

for(const [id,preset] of Object.entries(presets)) $("provider").add(new Option(preset.name??id,id));
$("provider").addEventListener("change",()=>{const preset=presets[$("provider").value];if(preset){$("baseUrl").value=preset.baseUrl;$("model").value=preset.model;}});
$("provider").dispatchEvent(new Event("change"));

async function mcpRequest(url,body){
  const headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"};
  if(mcpSessionId)headers["Mcp-Session-Id"]=mcpSessionId;
  const response=await fetch(url,{method:"POST",headers,body:JSON.stringify(body)});
  const sessionId=response.headers.get("Mcp-Session-Id");if(sessionId)mcpSessionId=sessionId;
  const contentType=response.headers.get("Content-Type")||"";const text=await response.text();
  if(!response.ok)throw new Error(text||`HTTP ${response.status}`);
  if(contentType.includes("text/event-stream")){const dataLines=text.split("\n").filter(line=>line.startsWith("data:")).map(line=>line.slice(5).trim()).filter(Boolean);if(!dataLines.length)throw new Error("MCP returned an empty event stream.");return JSON.parse(dataLines[dataLines.length-1]);}
  return text?JSON.parse(text):null;
}
async function connectMcp(){
  const url=$("mcpUrl").value.trim()||"/mcp";const status=$("mcpStatus");const button=$("mcpConnect");
  button.disabled=true;setStatus(status,"");mcpSessionId=null;mcpTools=[];
  try{
    log(`Connecting to MCP endpoint: ${url}`);
    const initialize=await mcpRequest(url,{jsonrpc:"2.0",id:1,method:"initialize",params:{protocolVersion:"2025-06-18",capabilities:{},clientInfo:{name:"mcp-playground",version:"0.4.0"}}});
    if(initialize?.error)throw new Error(initialize.error.message);log("MCP initialize completed.");
    const result=await mcpRequest(url,{jsonrpc:"2.0",id:2,method:"tools/list",params:{}});
    if(result?.error)throw new Error(result.error.message);
    mcpTools=result?.result?.tools||[];log(`tools/list returned ${mcpTools.length} tool(s).`);
    $("toolCount").textContent=mcpTools.length;$("mcpToolsSummary").textContent=mcpTools.length;$("toolCountBadge").textContent=mcpTools.length;
    const toolsElement=$("tools");toolsElement.innerHTML="";
    if(!mcpTools.length)toolsElement.innerHTML="<p>No tools were advertised by this server.</p>";
    else for(const tool of mcpTools){const element=document.createElement("div");element.className="tool";const name=document.createElement("strong");name.textContent=tool.name;const description=document.createElement("small");description.textContent=tool.description||"No description provided.";element.append(name,description);toolsElement.appendChild(element);}
    setStatus(status,"Connected",true);$("mcpCard").classList.add("connected");collapseConfig("mcpCard","mcpConfigBody");$("ask").disabled=!llmConnected;
  }catch(error){setStatus(status,`Connection failed: ${error.message}`);$("toolCount").textContent="0";$("mcpToolsSummary").textContent="0";$("toolCountBadge").textContent="0";$("mcpCard").classList.remove("connected");$("tools").innerHTML="<p>Unable to discover tools.</p>";log(`MCP error: ${error.message}`);}
  finally{button.disabled=false;}
}
$("mcpConnect").addEventListener("click",connectMcp);

async function connectLlm(){
  const url=$("baseUrl").value.trim().replace(/\/$/,"");const key=$("apiKey").value.trim();const model=$("model").value.trim();const status=$("llmStatus");const button=$("llmConnect");
  setStatus(status,"");if(!url||!model){setStatus(status,"Base URL and model are required.");return;}
  button.disabled=true;status.className="status";status.textContent="Testing LLM connection...";
  try{
    const headers={"Content-Type":"application/json"};if(key)headers.Authorization=`Bearer ${key}`;
    const response=await fetch(`${url}/chat/completions`,{method:"POST",headers,body:JSON.stringify({model,messages:[{role:"system",content:"Answer directly and concisely. Do not include internal analysis."},{role:"user",content:"Introduce yourself briefly by saying: I am [your model name]."}]})});
    const data=await response.json();if(!response.ok)throw new Error(data?.error?.message||`HTTP ${response.status}`);
    const message=data?.choices?.[0]?.message?.content;if(!message)throw new Error("The provider returned no assistant message.");
    status.textContent=message;status.classList.add("ok");llmConnected=true;$("llmModelSummary").textContent=model;$("llmCard").classList.add("connected");collapseConfig("llmCard","llmConfigBody");$("ask").disabled=mcpTools.length===0;
  }catch(error){llmConnected=false;$("llmCard").classList.remove("connected");$("llmModelSummary").textContent="Not connected";$("ask").disabled=true;setStatus(status,`Connection failed: ${error.message}`);}
  finally{button.disabled=false;}
}
$("llmConnect").addEventListener("click",connectLlm);

function toOpenAiTools(tools){return tools.map(tool=>({type:"function",function:{name:tool.name,description:tool.description||"",parameters:tool.inputSchema||{type:"object",properties:{}}}}));}

async function callLlm(messages,tools){
  const url=$("baseUrl").value.trim().replace(/\/$/,"");const key=$("apiKey").value.trim();const model=$("model").value.trim();const headers={"Content-Type":"application/json"};if(key)headers.Authorization=`Bearer ${key}`;
  const body={model,messages};if(tools.length)body.tools=toOpenAiTools(tools);
  const response=await fetch(`${url}/chat/completions`,{method:"POST",headers,body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw new Error(data?.error?.message||`HTTP ${response.status}`);
  const message=data?.choices?.[0]?.message;if(!message)throw new Error("The provider returned no assistant message.");
  return {message,usage:data?.usage||null};
}

async function callMcpTool(toolName,argumentsValue){
  const url=$("mcpUrl").value.trim()||"/mcp";
  const result=await mcpRequest(url,{jsonrpc:"2.0",id:Date.now(),method:"tools/call",params:{name:toolName,arguments:argumentsValue||{}}});
  if(result?.error)throw new Error(result.error.message);return result?.result;
}

$("ask").addEventListener("click",async()=>{
  const prompt=$("prompt").value.trim();const answer=$("answer");const button=$("ask");
  if(!prompt){answer.textContent="Enter a question first.";answer.classList.add("error");return;}
  if(!llmConnected){answer.textContent="Connect the LLM first.";answer.classList.add("error");return;}
  if(!mcpTools.length){answer.textContent="Connect to MCP and discover its tools first.";answer.classList.add("error");return;}
  button.disabled=true;$("answerPanel").classList.remove("hidden");answer.className="answer";answer.textContent="Thinking…";$("activity").innerHTML="<p>Waiting for tool activity...</p>";resetCommunicationLog();addCommunicationStep("Asking LLM");
  $("executionSummary").classList.add("hidden");
  try{
    const messages=[{role:"system",content:["You are using the Server Hub MCP server.","Use an MCP tool when it is needed to answer the user's question.","After receiving a tool result, answer the user directly and concisely.","Present results clearly for a human reader.","When the result contains tabular data, format it as a properly aligned Markdown table.","Use short paragraphs and bullet lists when appropriate.","Do not expose raw JSON, internal tool calls, or internal reasoning unless explicitly requested."].join(" ")},{role:"user",content:prompt}];
    log(`LLM request with ${mcpTools.length} MCP tool(s).`);
    const executionStartedAt=Date.now();let executionToolCount=0;let executionLlmTurns=0;
    const executionTokenUsage={prompt:0,completion:0,total:0,known:false};
    const maxToolRounds=12;let round=0;
    while(round<maxToolRounds){
      round+=1;const llmStartedAt=Date.now();const llmResponse=await callLlm(messages,mcpTools);const llmDuration=Date.now()-llmStartedAt;executionLlmTurns+=1;
      const assistantMessage=llmResponse.message;const usage=llmResponse.usage;
      let tokenInfo="tokens unavailable";
      if(usage&&typeof usage.total_tokens==="number"){executionTokenUsage.prompt+=usage.prompt_tokens||0;executionTokenUsage.completion+=usage.completion_tokens||0;executionTokenUsage.total+=usage.total_tokens;executionTokenUsage.known=true;tokenInfo=`${usage.total_tokens.toLocaleString()} tokens`;}
      const toolCalls=assistantMessage.tool_calls||[];
      if(!toolCalls.length){
        addCommunicationStep(`LLM response received · ${llmDuration} ms · ${tokenInfo}`,"done");
        $("answerPanel").classList.remove("hidden");answer.innerHTML=renderMarkdown(assistantMessage.content||"The model returned no final answer.");
        updateExecutionSummary(executionToolCount,executionLlmTurns,executionStartedAt,executionTokenUsage);
        addCommunicationStep("Final LLM response received","done");log("Final LLM response received.");return;
      }
      addCommunicationStep(`LLM response received · ${llmDuration} ms · ${tokenInfo}`,"done");messages.push(assistantMessage);
      for(const toolCall of toolCalls){
        const toolName=toolCall.function?.name;if(!toolName)throw new Error("LLM returned a tool call without a function name.");
        let argumentsValue={};try{argumentsValue=JSON.parse(toolCall.function?.arguments||"{}");}catch{throw new Error(`Invalid arguments returned for ${toolName}.`);}
        executionToolCount+=1;addCommunicationStep(`LLM requested tool calling ${toolName}`);log(`LLM requested MCP tool: ${toolName}`);
        const toolStartedAt=Date.now();const toolResult=await callMcpTool(toolName,argumentsValue);const toolDuration=Date.now()-toolStartedAt;
        addCommunicationStep(`Tool calling response received · ${toolDuration} ms`,"done");renderActivity(toolName,argumentsValue,toolResult);
        messages.push({role:"tool",tool_call_id:toolCall.id,content:JSON.stringify(toolResult)});addCommunicationStep("Informing LLM");
      }
    }
    throw new Error(`Maximum MCP tool rounds (${maxToolRounds}) exceeded.`);
  }catch(error){addCommunicationStep(error.message,"error");$("answerPanel").classList.remove("hidden");answer.textContent=`Error: ${error.message}`;answer.className="answer error";log(`Orchestration error: ${error.message}`);}
  finally{button.disabled=false;}
});

document.addEventListener("click",(event)=>{
  const button=event.target.closest(".example-button");if(!button)return;const field=$("prompt");if(!field)return;field.value=button.dataset.prompt||"";field.focus();field.dispatchEvent(new Event("input",{bubbles:true}));
});
