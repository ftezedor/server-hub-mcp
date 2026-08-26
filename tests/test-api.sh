#!/usr/bin/env bash

set -u

BASE_URL="${BASE_URL:-http://localhost:8080}"
LOG_FILE="${LOG_FILE:-/tmp/mcp-hub/api-test-$(date +%Y%m%d-%H%M%S).log}"

mkdir -p "$(dirname "$LOG_FILE")"

PASS=0
FAIL=0

log() {
    echo "$*" | tee -a "$LOG_FILE"
}

separator() {
    log
    log "================================================================"
    log "$*"
    log "================================================================"
}

request() {
    local method="$1"
    local path="$2"
    local expected="$3"
    local body="${4:-}"

    local url="${BASE_URL}${path}"
    local response
    local status
    local http_code

    log
    log ">>> ${method} ${url}"

    if [[ -n "$body" ]]; then
        log "Request body:"
        log "$body"
    fi

    if [[ "$method" == "GET" ]]; then
        response=$(curl -sS \
            -w $'\n__HTTP_STATUS__%{http_code}' \
            "$url" 2>&1)
    else
        response=$(curl -sS \
            -w $'\n__HTTP_STATUS__%{http_code}' \
            -X "$method" \
            -H "Content-Type: application/json" \
            -d "$body" \
            "$url" 2>&1)
    fi

    http_code=$(printf '%s\n' "$response" | sed -n 's/^__HTTP_STATUS__//p')
    response=$(printf '%s\n' "$response" | sed '/^__HTTP_STATUS__/d')

    log "HTTP ${http_code}"
    log "Response:"
    log "$response"

    if [[ "$http_code" == "$expected" ]]; then
        log "RESULT: PASS"
        ((PASS++))
    else
        log "RESULT: FAIL (expected HTTP ${expected})"
        ((FAIL++))
    fi
}

separator "MCP HUB REST API TEST"

log "Base URL : ${BASE_URL}"
log "Log file : ${LOG_FILE}"
log "Started  : $(date)"

# ------------------------------------------------------------------
# Health / OpenAPI
# ------------------------------------------------------------------

separator "HEALTH / API METADATA"

request GET "/docs" 200
request GET "/redoc" 200
request GET "/openapi.json" 200

request GET "/" 200

# ------------------------------------------------------------------
# SERVERS
# ------------------------------------------------------------------

separator "SERVERS"

request GET "/api/servers" 200

# Create server
request POST "/api/servers" 201 \
'{
  "name": "api-test-server",
  "ip": "10.99.99.10",
  "environment": "development",
  "status": "online",
  "cpu_cores": 4,
  "memory_gb": 8,
  "disk_gb": 100
}'

# Update server status
request PUT "/api/servers/1/status?status=maintenance" 200

# Delete server
request DELETE "/api/servers/999999" 404

# Existing server
request GET "/api/servers/1" 200

# Non-existing server
request GET "/api/servers/999999" 404

# Search
request GET "/api/search?q=web" 200

# Empty search should be rejected if that is the API contract
request GET "/api/search?q=" 422

# ------------------------------------------------------------------
# METRICS
# ------------------------------------------------------------------

separator "METRICS"

request GET "/api/servers/1/metrics" 200

request GET "/api/servers/1/metrics?limit=1" 200

request GET "/api/servers/1/metrics?limit=50" 200

# Validation
request GET "/api/servers/1/metrics?limit=0" 422
request GET "/api/servers/1/metrics?limit=999" 422

# Non-existing server
request GET "/api/servers/999999/metrics" 404

# Add metrics
request POST "/api/servers/1/metrics" 201 \
'{
  "cpu_usage_percent": 42.5,
  "memory_usage_percent": 55.0,
  "disk_usage_percent": 61.0,
  "temperature_celsius": 65.0,
  "uptime_seconds": 1932000
}'

# ------------------------------------------------------------------
# ALERTS
# ------------------------------------------------------------------

separator "ALERTS"

# List
request GET "/api/alerts" 200

# Create valid alert
request POST "/api/alerts" 201 \
'{
  "server": "web-server-01",
  "severity": "warning",
  "message": "Automated REST API integration test"
}'

# Unknown server
request POST "/api/alerts" 404 \
'{
  "server": "does-not-exist",
  "severity": "warning",
  "message": "Should fail"
}'

# Invalid severity
request POST "/api/alerts" 422 \
'{
  "server": "web-server-01",
  "severity": "invalid",
  "message": "Should fail"
}'

# Missing server
request POST "/api/alerts" 422 \
'{
  "severity": "warning",
  "message": "Should fail"
}'

# Missing severity
request POST "/api/alerts" 422 \
'{
  "server": "web-server-01",
  "message": "Should fail"
}'

# Missing message
request POST "/api/alerts" 422 \
'{
  "server": "web-server-01",
  "severity": "warning"
}'

# ------------------------------------------------------------------
# SYSTEM
# ------------------------------------------------------------------

separator "SYSTEM"

request GET "/api/stats" 200

# ------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------

separator "TEST SUMMARY"

log "PASS: ${PASS}"
log "FAIL: ${FAIL}"
log "TOTAL: $((PASS + FAIL))"
log
log "Finished : $(date)"
log "Log      : ${LOG_FILE}"

if (( FAIL > 0 )); then
    log
    log "❌ API TEST SUITE FAILED"
    exit 1
else
    log
    log "✅ API TEST SUITE PASSED"
    exit 0
fi