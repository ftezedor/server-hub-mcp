#!/usr/bin/env bash
#
# test-mcp.sh - MCP integration/regression test suite
#
# test-mcp.sh = actual tests
# This suite invokes mcp-cli directly; wrappers are not used.
#

set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

MCP_CLI="${MCP_CLI:-mcp-cli}"
MCP_CMD="$PROJECT_DIR/scripts/mcp-cmd.sh"

CONFIG_FILE="/tmp/mcp_cli_test_config.json"
SERVER_NAME="server-hub"
OUTPUT_FILE="/tmp/mcp-test-output-$$.log"

PASS=0
FAIL=0
SKIP=0
TOTAL=0

RUN_LOCAL=1
RUN_REMOTE=1
RUN_PROMPTS=1

cleanup() {
    rm -f "$OUTPUT_FILE" "$CONFIG_FILE"
}
trap cleanup EXIT

section() {
    echo
    echo "================================================================"
    echo "$1"
    echo "================================================================"
}

pass() {
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
    printf '✓ PASS: %s\n' "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
    printf '✗ FAIL: %s\n' "$1"
}

skip() {
    SKIP=$((SKIP + 1))
    TOTAL=$((TOTAL + 1))
    printf '⚠ SKIP: %s\n' "$1"
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --local-only       Run only local/stdio MCP tests
  --remote-only      Run only remote/HTTP MCP tests
  --skip-prompts     Skip LLM/prompt tests
  -h, --help         Show this help
EOF
}


configure_local() {
    cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "$SERVER_NAME": {
      "command": "$PROJECT_DIR/venv/bin/python3.12",
      "args": [
        "$PROJECT_DIR/app/mcp/local_server.py"
      ]
    }
  }
}
EOF
}

configure_remote() {
    cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "$SERVER_NAME": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
EOF
}

# Execute mcp-cli directly.
run_mcp() {
    local mode="$1"
    shift

    case "$mode" in
        local) configure_local ;;
        remote) configure_remote ;;
        *) return 2 ;;
    esac

    "$MCP_CLI" "$@" \
        --server "$SERVER_NAME" \
        --config-file "$CONFIG_FILE"
}

assert_success() {
    local name="$1"
    shift

    if "$@" >"$OUTPUT_FILE" 2>&1; then
        pass "$name"
        return 0
    fi

    fail "$name"
    cat "$OUTPUT_FILE"
    return 1
}

# mcp-cli may return exit code 0 even when the MCP tool itself reports
# an execution/validation error. Negative tests therefore assert on the
# actual MCP error response rather than the process exit status.
assert_tool_error() {
    local name="$1"
    shift

    "$@" >"$OUTPUT_FILE" 2>&1
    local rc=$?

    if grep -Eiq \
        'Tool execution failed|Error calling tool|validation error|Missing required argument|Input should|not found|must not be empty|greater than or equal|less than or equal' \
        "$OUTPUT_FILE"; then
        pass "$name"
        return 0
    fi

    fail "$name"
    echo "Command exit code: $rc"
    cat "$OUTPUT_FILE"
    return 1
}

assert_contains() {
    local name="$1"
    local expected="$2"
    shift 2

    if "$@" >"$OUTPUT_FILE" 2>&1 &&
       grep -Fq "$expected" "$OUTPUT_FILE"; then
        pass "$name"
        return 0
    fi

    fail "$name"
    cat "$OUTPUT_FILE"
    return 1
}

test_discovery() {
    local mode="$1"

    section "MCP DISCOVERY - ${mode^^}"

    assert_success \
        "$mode: tools/list executes" \
        run_mcp "$mode" tools

    local tool
    for tool in \
        search_servers \
        get_server \
        get_server_metrics \
        get_active_alerts \
        get_system_stats \
        create_alert
    do
        assert_contains \
            "$mode: tool discovered: $tool" \
            "$tool" \
            run_mcp "$mode" tools
    done
}

test_valid_tools() {
    local mode="$1"
    local marker="MCP_TEST_$(date +%s)_$$"

    section "VALID TOOL CALLS - ${mode^^}"

    assert_success \
        "$mode: get_system_stats" \
        run_mcp "$mode" cmd --tool get_system_stats

    assert_success \
        "$mode: get_active_alerts" \
        run_mcp "$mode" cmd --tool get_active_alerts

    assert_success \
        "$mode: search_servers by name" \
        run_mcp "$mode" cmd --tool search_servers \
        --tool-args '{"query":"web"}'

    assert_success \
        "$mode: search_servers by IP" \
        run_mcp "$mode" cmd --tool search_servers \
        --tool-args '{"query":"192.168.1.10"}'

    assert_success \
        "$mode: get_server by name" \
        run_mcp "$mode" cmd --tool get_server \
        --tool-args '{"server":"web-server-01"}'

    assert_success \
        "$mode: get_server by IP" \
        run_mcp "$mode" cmd --tool get_server \
        --tool-args '{"server":"192.168.1.10"}'

    assert_success \
        "$mode: get_server_metrics default limit" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{"server":"web-server-01"}'

    assert_success \
        "$mode: get_server_metrics limit=1" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{"server":"web-server-01","limit":1}'

    assert_success \
        "$mode: get_server_metrics limit=50" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{"server":"web-server-01","limit":50}'

    assert_success \
        "$mode: create_alert" \
        run_mcp "$mode" cmd --tool create_alert \
        --tool-args "{\"server\":\"web-server-01\",\"severity\":\"warning\",\"message\":\"$marker\"}"
}

test_error_cases() {
    local mode="$1"

    section "ERROR / VALIDATION TESTS - ${mode^^}"

    assert_tool_error \
        "$mode: unknown tool" \
        run_mcp "$mode" cmd --tool does_not_exist

    assert_tool_error \
        "$mode: get_server missing argument" \
        run_mcp "$mode" cmd --tool get_server \
        --tool-args '{}'

    assert_tool_error \
        "$mode: get_server unknown server" \
        run_mcp "$mode" cmd --tool get_server \
        --tool-args '{"server":"does-not-exist"}'

    assert_tool_error \
        "$mode: get_server unknown IP" \
        run_mcp "$mode" cmd --tool get_server \
        --tool-args '{"server":"10.255.255.255"}'

    assert_tool_error \
        "$mode: search_servers empty query" \
        run_mcp "$mode" cmd --tool search_servers \
        --tool-args '{"query":""}'

    assert_tool_error \
        "$mode: get_server_metrics missing server" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{}'

    assert_tool_error \
        "$mode: get_server_metrics unknown server" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{"server":"does-not-exist"}'

    assert_tool_error \
        "$mode: get_server_metrics limit=0" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{"server":"web-server-01","limit":0}'

    assert_tool_error \
        "$mode: get_server_metrics limit=51" \
        run_mcp "$mode" cmd --tool get_server_metrics \
        --tool-args '{"server":"web-server-01","limit":51}'

    assert_tool_error \
        "$mode: create_alert unknown server" \
        run_mcp "$mode" cmd --tool create_alert \
        --tool-args '{"server":"does-not-exist","severity":"warning","message":"MCP test"}'

    assert_tool_error \
        "$mode: create_alert invalid severity" \
        run_mcp "$mode" cmd --tool create_alert \
        --tool-args '{"server":"web-server-01","severity":"invalid","message":"MCP test"}'

    assert_tool_error \
        "$mode: create_alert missing message" \
        run_mcp "$mode" cmd --tool create_alert \
        --tool-args '{"server":"web-server-01","severity":"warning"}'
}

test_write_read() {
    local mode="$1"
    local marker="MCP_WRITE_READ_$(date +%s)_$$"

    section "WRITE / READ INTEGRATION - ${mode^^}"

    if run_mcp "$mode" cmd --tool create_alert \
        --tool-args "{\"server\":\"web-server-01\",\"severity\":\"info\",\"message\":\"$marker\"}" \
        >"$OUTPUT_FILE" 2>&1; then
        pass "$mode: create test alert"
    else
        fail "$mode: create test alert"
        cat "$OUTPUT_FILE"
        return
    fi

    if run_mcp "$mode" cmd --tool get_active_alerts >"$OUTPUT_FILE" 2>&1 &&
       grep -Fq "$marker" "$OUTPUT_FILE"; then
        pass "$mode: created alert returned by get_active_alerts"
    else
        fail "$mode: created alert returned by get_active_alerts"
        cat "$OUTPUT_FILE"
    fi
}

test_repeated_calls() {
    local mode="$1"

    section "REPEATED CALLS - ${mode^^}"

    local i
    for i in 1 2 3 4 5; do
        if ! run_mcp "$mode" cmd --tool get_system_stats >"$OUTPUT_FILE" 2>&1; then
            fail "$mode: five consecutive tool calls"
            echo "Call $i failed:"
            cat "$OUTPUT_FILE"
            return
        fi
    done

    pass "$mode: five consecutive tool calls"
}

run_prompt() {
    local mode="$1"
    local prompt="$2"

    case "$mode" in
        local) configure_local ;;
        remote) configure_remote ;;
    esac

    # if "$MCP_CLI" cmd \
    #     --server "$SERVER_NAME" \
    #     --config-file "$CONFIG_FILE" \
    #     -p "$prompt" >"$OUTPUT_FILE" 2>&1; then
    if "$MCP_CMD" "$prompt" > "$OUTPUT_FILE" 2>&1; then
        pass "$mode: prompt - $prompt"
    else
        fail "$mode: prompt - $prompt"
        cat "$OUTPUT_FILE"
    fi
}

test_prompts() {
    local mode="$1"

    section "PROMPT TESTS - ${mode^^}"

    run_prompt "$mode" "Are there any problems with production servers?"
    run_prompt "$mode" "Why is web-server-01 concerning?"
    run_prompt "$mode" "Compare the current health of web-server-01 and web-server-02."
    run_prompt "$mode" "Find the web servers and tell me their current status and whether any have active alerts."
    run_prompt "$mode" "Which server has the highest CPU usage based on the available metrics?"
    run_prompt "$mode" "Are there any critical alerts on database servers?"
}

run_transport_tests() {
    local mode="$1"

    test_discovery "$mode"
    test_valid_tools "$mode"
    test_error_cases "$mode"
    test_write_read "$mode"
    test_repeated_calls "$mode"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --local-only)
            RUN_REMOTE=0
            ;;
        --remote-only)
            RUN_LOCAL=0
            ;;
        --skip-prompts)
            RUN_PROMPTS=0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

section "MCP TEST SUITE"

echo "Project : $PROJECT_DIR"
echo "Server  : $SERVER_NAME"
echo "Started : $(date '+%Y-%m-%d %H:%M:%S %z')"

if ! command -v "$MCP_CLI" >/dev/null 2>&1; then
    echo "ERROR: mcp-cli not found: $MCP_CLI" >&2
    exit 1
fi

if [[ "$RUN_LOCAL" -eq 1 ]]; then
    run_transport_tests local
else
    skip "local transport tests"
fi

if [[ "$RUN_REMOTE" -eq 1 ]]; then
    run_transport_tests remote
else
    skip "remote transport tests"
fi

if [[ "$RUN_PROMPTS" -eq 1 ]]; then
    [[ "$RUN_LOCAL" -eq 1 ]] && test_prompts local
    [[ "$RUN_REMOTE" -eq 1 ]] && test_prompts remote
else
    skip "prompt tests"
fi

section "TEST SUMMARY"

echo "PASS : $PASS"
echo "FAIL : $FAIL"
echo "SKIP : $SKIP"
echo "TOTAL: $TOTAL"
echo
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S %z')"

if [[ "$FAIL" -eq 0 ]]; then
    echo
    echo "✅ MCP TEST SUITE PASSED"
    exit 0
fi

echo
echo "❌ MCP TEST SUITE FAILED"
exit 1
