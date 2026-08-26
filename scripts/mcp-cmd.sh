# set -x 

CONFIG_FILE="/tmp/mcp_cli_config.json"
SERVER_NAME="server-hub"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"


MCP_DIR="$PROJECT_DIR/app/mcp"


AI_API_BASE="https://api.roteia.ai/v1/chat/completions"
AI_PROVIDER="openai_compatible"
AI_MODEL="nvidia/nemotron-3.5-lightning:free"

# AI_MODEL="openai/gpt-oss-120b"
# AI_MODEL="openai/gpt-oss-safeguard-20b"

if [ -z "$1" ]; then
    echo "Usage: $0 <prompt>"
    exit 1
fi

# ============================================================
# HELPER FUNCTIONS
# ============================================================

# cd "$SCRIPT_DIR"/.. || exit 1

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================
# CONFIGURATION CREATION
# ============================================================
check_config() {
    [ -f "$CONFIG_FILE" ] || {
        print_error "Configuration not found"
        print_error "run with configure local or configure remote"
        exit 1
    }
}

configure() {
    if [ "$1" == "local" ]; then
        create_local_config
    elif [ "$1" == "remote" ]; then
        create_remote_config
    else
        print_error "Unknown configuration type: $1 (local or remote)"
        exit 1
    fi
}

create_local_config() {

    print_header "Creating MCP CLI configuration (stdio server)"
    
    cat > "$CONFIG_FILE" << EOF
{
    "mcpServers": {
        "$SERVER_NAME": {
            "command": "$PROJECT_DIR/venv/bin/python3.12",
            "args": [
                "$MCP_DIR/local_server.py"
            ]
        }
    }
}
EOF
    
    print_success "Configuration created at: $CONFIG_FILE"
}

create_remote_config() {

    print_header "Creating MCP CLI configuration (http server)"
    
    cat > "$CONFIG_FILE" << EOF
{
    "mcpServers": {
        "$SERVER_NAME": {
            "url": "http://localhost:8000/mcp"
        }
    }
}
EOF
    
    print_success "Configuration created at: $CONFIG_FILE"
}

COMMAND="${1}"

case "$COMMAND" in
    configure)
        shift
        configure "$1"
        exit 0
        ;;
esac

check_config

MCP_SYSTEM_PROMPT='
TOOL FAILURE AND EVIDENCE AVAILABILITY

Treat tool execution failures and incomplete tool results as explicit
absence of evidence.

Classify information as:

FACT
  Information directly returned by a successful MCP tool call.

UNAVAILABLE
  Information that could not be obtained because a tool failed,
  returned unusable data, or did not provide the requested field.

INFERENCE
  A conclusion derived from available facts.

Rules:

1. Never present UNAVAILABLE information as FACT.
2. Never fill missing information using assumptions, prior knowledge,
   or information not returned by the MCP tools.
3. If a required tool fails, explicitly state what information is
   unavailable.
4. Distinguish observed facts from conclusions derived from those facts.
5. If MCP tools return conflicting information, explicitly report
   the conflict instead of arbitrarily choosing one result.
6. Prefer an incomplete but evidence-grounded answer over a complete
   answer based on unsupported assumptions.
7. A successful tool call does not make information from other failed
   tools available by implication.
8. Do not characterize a state, event, or action as expected, normal,
   planned, intentional, or resolved unless the MCP data explicitly
   supports that characterization.
'

cd "$PROJECT_DIR" || exit 1

OPENAI_BASE_URL="https://api.roteia.ai/v1" 
OPENAI_API_KEY="rt-live-DbT7DS3xegN2HvnAThXboOG1ElCL3H1I" 

export OPENAI_BASE_URL
export OPENAI_API_KEY

mcp-cli cmd --quiet \
   --server "$SERVER_NAME" \
   --config-file "$CONFIG_FILE" \
   --api-base "$AI_API_BASE" \
   --provider "$AI_PROVIDER" \
   --model "$AI_MODEL" \
   --api-key "$AI_API_KEY" \
   --system-prompt "$MCP_SYSTEM_PROMPT" \
   -p "$@"