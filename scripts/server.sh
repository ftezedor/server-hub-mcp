#!/bin/bash
# server.sh - Gerenciador de Servidores MCP Hub
# Uso: ./server.sh [api|mcp] [start|stop|status|restart]

# ============================================================
# CONFIGURAÇÕES
# ============================================================

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_DIR=$(dirname "$SCRIPT_DIR")
PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
VENV_DIR="$PROJECT_DIR/venv"
PID_DIR="/tmp/mcp-hub"

API_PID_FILE="$PID_DIR/api.pid"
MCP_PID_FILE="$PID_DIR/mcp.pid"
API_LOG="$PID_DIR/api.log"
MCP_LOG="$PID_DIR/mcp.log"

# Hosts
API_HOST="0.0.0.0"
MCP_HOST="0.0.0.0"

# Portas
API_PORT=8080
MCP_PORT=8000

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

# Cria diretório de PIDs se não existir
ensure_pid_dir() {
    if [ ! -d "$PID_DIR" ]; then
        mkdir -p "$PID_DIR"
    fi
}

# Verifica se um processo está rodando pelo PID
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Verifica se a porta está em uso
is_port_in_use() {
    local port=$1
    if netstat -tulpn 2>/dev/null | grep -q ":$port "; then
        return 0
    fi
    if ss -tulpn 2>/dev/null | grep -q ":$port "; then
        return 0
    fi
    return 1
}

# ============================================================
# SERVER: API (REST na porta 8080)
# ============================================================

api_start() {
    ensure_pid_dir
    
    if is_running "$API_PID_FILE"; then
        echo "❌ API Server já está rodando (PID: $(cat $API_PID_FILE))"
        return 1
    fi
    
    if is_port_in_use "$API_PORT"; then
        echo "❌ Porta $API_PORT já está em uso"
        return 1
    fi
    
    echo "🚀 Iniciando API Server (porta $API_PORT)..."
    
    cd "$PROJECT_DIR" || return 1
    source "$VENV_DIR/bin/activate" || return 1
    
    nohup python3.12 ./app/api/server.py --host 0.0.0.0 --port $API_PORT >> "$API_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$API_PID_FILE"
    
    sleep 2
    
    if is_running "$API_PID_FILE"; then
        echo "✅ API Server iniciado com sucesso!"
        echo "   📖 Swagger UI: http://$API_HOST:$API_PORT/docs"
        echo "   📚 ReDoc:      http://$API_HOST:$API_PORT/redoc"
        echo "   📋 PID:        $pid"
        echo "   📄 Log:        $API_LOG"
    else
        echo "❌ Falha ao iniciar API Server. Verifique o log: $API_LOG"
        return 1
    fi
}

api_stop() {
    if ! is_running "$API_PID_FILE"; then
        echo "⚠️ API Server não está rodando"
        return 1
    fi
    
    local pid=$(cat "$API_PID_FILE")
    echo "🛑 Parando API Server (PID: $pid)..."
    
    kill "$pid" 2>/dev/null
    sleep 2
    
    # Força kill se ainda estiver rodando
    if is_running "$API_PID_FILE"; then
        echo "⚠️ Processo não respondeu, forçando kill..."
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi
    
    rm -f "$API_PID_FILE"
    echo "✅ API Server parado"
}

api_status() {
    if is_running "$API_PID_FILE"; then
        local pid=$(cat "$API_PID_FILE")
        echo "✅ API Server: RODANDO (PID: $pid, Porta: $API_PORT)"
        echo "   📖 Swagger: http://$API_HOST:$API_PORT/docs"
        if is_port_in_use "$API_PORT"; then
            echo "   🌐 Porta $API_PORT: EM USO"
        else
            echo "   ⚠️ Porta $API_PORT: NÃO ESTÁ ESCUTANDO"
        fi
    else
        echo "❌ API Server: PARADO"
    fi
}

# ============================================================
# SERVER: MCP (na porta 8000)
# ============================================================

mcp_start() {
    ensure_pid_dir
    
    if is_running "$MCP_PID_FILE"; then
        echo "❌ MCP Server já está rodando (PID: $(cat $MCP_PID_FILE))"
        return 1
    fi
    
    if is_port_in_use "$MCP_PORT"; then
        echo "❌ Porta $MCP_PORT já está em uso"
        return 1
    fi
    
    echo "🚀 Iniciando MCP Server (porta $MCP_PORT)..."
    
    cd "$PROJECT_DIR" || return 1
    source "$VENV_DIR/bin/activate" || return 1
    
    export SERVER_HUB_MCP_BACKEND="application"

    nohup python3.12 ./app/mcp/http_server.py --host 0.0.0.0 --port $MCP_PORT >> "$MCP_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$MCP_PID_FILE"
    
    sleep 2
    
    if is_running "$MCP_PID_FILE"; then
        echo "✅ MCP Server iniciado com sucesso!"
        echo "   📍 Endpoint: http://$MCP_HOST:$MCP_PORT/mcp"
        echo "   📋 PID:      $pid"
        echo "   📄 Log:      $MCP_LOG"
    else
        echo "❌ Falha ao iniciar MCP Server. Verifique o log: $MCP_LOG"
        return 1
    fi
}

mcp_stop() {
    if ! is_running "$MCP_PID_FILE"; then
        echo "⚠️ MCP Server não está rodando"
        return 1
    fi
    
    local pid=$(cat "$MCP_PID_FILE")
    echo "🛑 Parando MCP Server (PID: $pid)..."
    
    kill "$pid" 2>/dev/null
    sleep 2
    
    if is_running "$MCP_PID_FILE"; then
        echo "⚠️ Processo não respondeu, forçando kill..."
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi
    
    rm -f "$MCP_PID_FILE"
    echo "✅ MCP Server parado"
}

mcp_status() {
    if is_running "$MCP_PID_FILE"; then
        local pid=$(cat "$MCP_PID_FILE")
        echo "✅ MCP Server: RODANDO (PID: $pid, Porta: $MCP_PORT)"
        echo "   📍 Endpoint: http://$MCP_HOST:$MCP_PORT/mcp"
        if is_port_in_use "$MCP_PORT"; then
            echo "   🌐 Porta $MCP_PORT: EM USO"
        else
            echo "   ⚠️ Porta $MCP_PORT: NÃO ESTÁ ESCUTANDO"
        fi
    else
        echo "❌ MCP Server: PARADO"
    fi
}

# ============================================================
# COMANDOS: Ambos
# ============================================================

both_start() {
    echo "🚀 Iniciando ambos os servidores..."
    echo ""
    api_start
    echo ""
    mcp_start
    echo ""
    echo "📊 Resumo:"
    api_status
    mcp_status
}

both_stop() {
    echo "🛑 Parando ambos os servidores..."
    echo ""
    api_stop
    echo ""
    mcp_stop
}

both_status() {
    echo "📊 Status dos Servidores:"
    echo "================================"
    api_status
    echo ""
    mcp_status
}

both_restart() {
    both_stop
    sleep 2
    both_start
}

# ============================================================
# LOGS
# ============================================================

show_logs() {
    local server=$1
    local lines=${2:-50}
    
    case $server in
        api)
            if [ -f "$API_LOG" ]; then
                echo "📄 Últimas $lines linhas do API Server:"
                echo "================================"
                tail -n "$lines" "$API_LOG"
            else
                echo "❌ Log da API não encontrado: $API_LOG"
            fi
            ;;
        mcp)
            if [ -f "$MCP_LOG" ]; then
                echo "📄 Últimas $lines linhas do MCP Server:"
                echo "================================"
                tail -n "$lines" "$MCP_LOG"
            else
                echo "❌ Log do MCP não encontrado: $MCP_LOG"
            fi
            ;;
        *)
            echo "📄 Últimas $lines linhas do API Server:"
            echo "================================"
            tail -n "$lines" "$API_LOG" 2>/dev/null || echo "Log não encontrado"
            echo ""
            echo "📄 Últimas $lines linhas do MCP Server:"
            echo "================================"
            tail -n "$lines" "$MCP_LOG" 2>/dev/null || echo "Log não encontrado"
            ;;
    esac
}

# ============================================================
# HELP
# ============================================================

show_help() {
    echo "🔧 MCP Hub Server Manager"
    echo ""
    echo "Uso: ./server.sh [COMANDO] [OPÇÕES]"
    echo ""
    echo "COMANDOS:"
    echo "  api start               Inicia o API Server (porta $API_PORT)"
    echo "  api stop                Para o API Server"
    echo "  api status              Status do API Server"
    echo "  api restart             Reinicia o API Server"
    echo "  api logs [N]            Mostra últimas N linhas do log da API (padrão: 50)"
    echo ""
    echo "  mcp start               Inicia o MCP Server (porta $MCP_PORT)"
    echo "  mcp stop                Para o MCP Server"
    echo "  mcp status              Status do MCP Server"
    echo "  mcp restart             Reinicia o MCP Server"
    echo "  mcp logs [N]            Mostra últimas N linhas do log do MCP (padrão: 50)"
    echo ""
    echo "  all start               Inicia ambos os servidores"
    echo "  all stop                Para ambos os servidores"
    echo "  all status              Status de ambos os servidores"
    echo "  all restart             Reinicia ambos os servidores"
    echo "  all logs [N]            Mostra logs de ambos os servidores"
    echo ""
    echo "  help                    Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  ./server.sh api start"
    echo "  ./server.sh mcp status"
    echo "  ./server.sh all restart"
    echo "  ./server.sh api logs 30"
}

# ============================================================
# MAIN
# ============================================================

case "${1:-help}" in
    api)
        case "${2:-status}" in
            start)   api_start ;;
            stop)    api_stop ;;
            status)  api_status ;;
            restart) api_stop; sleep 1; api_start ;;
            logs)    show_logs api "${3:-50}" ;;
            *)       echo "❌ Uso: $0 api {start|stop|status|restart|logs}"; exit 1 ;;
        esac
        ;;
    mcp)
        case "${2:-status}" in
            start)   mcp_start ;;
            stop)    mcp_stop ;;
            status)  mcp_status ;;
            restart) mcp_stop; sleep 1; mcp_start ;;
            logs)    show_logs mcp "${3:-50}" ;;
            *)       echo "❌ Uso: $0 mcp {start|stop|status|restart|logs}"; exit 1 ;;
        esac
        ;;
    all)
        case "${2:-status}" in
            start)   both_start ;;
            stop)    both_stop ;;
            status)  both_status ;;
            restart) both_restart ;;
            logs)    show_logs all "${3:-50}" ;;
            *)       echo "❌ Uso: $0 all {start|stop|status|restart|logs}"; exit 1 ;;
        esac
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Comando desconhecido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac