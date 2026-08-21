#!/usr/bin/env python3
# server.py - API REST na porta 8080

import sys
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import uvicorn

# Database imports (compartilhados)
from database import (
    get_all_servers,
    get_server_by_id,
    get_server_by_name,
    update_server_status,
    get_latest_metrics,
    get_metrics_history,
    get_active_alerts,
    create_alert,
    add_metrics,
    delete_server,
    create_server,
    init_database
)
from models import Server, ServerMetrics, ServerAlert

# ============================================================
# 1. MODELOS PYDANTIC
# ============================================================

class ServerCreate(BaseModel):
    name: str = Field(..., description="Nome único do servidor", example="web-server-01")
    ip: str = Field(..., description="Endereço IP do servidor", example="192.168.1.10")
    environment: str = Field(..., description="Ambiente: production, staging, development", example="production")
    status: str = Field(default="online", description="Status: online, offline, maintenance", example="online")
    cpu_cores: int = Field(..., description="Núcleos de CPU", example=8, ge=1)
    memory_gb: float = Field(..., description="Memória RAM em GB", example=16.0, ge=1)
    disk_gb: float = Field(..., description="Espaço em disco em GB", example=500.0, ge=1)


class MetricsCreate(BaseModel):
    cpu_usage_percent: float = Field(..., description="Uso de CPU em %", example=45.5, ge=0, le=100)
    memory_usage_percent: float = Field(..., description="Uso de memória em %", example=62.3, ge=0, le=100)
    disk_usage_percent: float = Field(..., description="Uso de disco em %", example=71.8, ge=0, le=100)
    temperature_celsius: Optional[float] = Field(None, description="Temperatura em °C", example=42.5)
    uptime_seconds: int = Field(..., description="Tempo de atividade em segundos", example=86400)


class AlertCreate(BaseModel):
    server_id: int = Field(..., description="ID do servidor", example=1)
    severity: str = Field(..., description="Severidade: critical, warning, info", example="warning")
    message: str = Field(..., description="Mensagem do alerta", example="Uso de CPU acima de 80%")


# ============================================================
# 2. FASTAPI - REST API (porta 8080)
# ============================================================

tags_metadata = [
    {"name": "Root", "description": "Informações gerais da API"},
    {"name": "Servidores", "description": "Operações de gerenciamento de servidores"},
    {"name": "Métricas", "description": "Coleta e histórico de métricas"},
    {"name": "Alertas", "description": "Gerenciamento de alertas do sistema"},
    {"name": "Busca", "description": "Pesquisa de servidores"},
]

app = FastAPI(
    title="MCP Server Hub API",
    version="2.0.0",
    contact={"name": "Seu Nome", "email": "seu@email.com"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    }
)

app.openapi_tags = tags_metadata


# ============================================================
# 3. ENDPOINTS DA API
# ============================================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "MCP Server Hub API",
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/api/servers", tags=["Servidores"])
async def list_servers():
    servers = get_all_servers()
    return {"servers": servers, "total": len(servers)}


@app.get("/api/servers/{server_id}", tags=["Servidores"])
async def get_server(server_id: int):
    server = get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    metrics = get_latest_metrics(server_id)
    server["metrics"] = metrics
    return server


@app.post("/api/servers", tags=["Servidores"], status_code=status.HTTP_201_CREATED)
async def create_server_endpoint(server: ServerCreate):
    existing = get_server_by_name(server.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Servidor com nome '{server.name}' já existe (ID: {existing['id']})"
        )
    server_id = create_server(server)
    return {"id": server_id, "message": f"Servidor '{server.name}' criado com sucesso"}


@app.put("/api/servers/{server_id}/status", tags=["Servidores"])
async def update_status(server_id: int, status: str = Query(..., example="offline")):
    server = get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    if status not in ["online", "offline", "maintenance"]:
        raise HTTPException(status_code=400, detail="Status inválido")
    update_server_status(server_id, status)
    return {"message": f"Status atualizado para '{status}'", "server_id": server_id}


@app.delete("/api/servers/{server_id}", tags=["Servidores"])
async def delete_server_endpoint(server_id: int):
    server = get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    delete_server(server_id)
    return {"message": f"Servidor '{server['name']}' removido com sucesso"}


@app.get("/api/servers/{server_id}/metrics", tags=["Métricas"])
async def get_metrics(server_id: int, limit: int = Query(10, ge=1, le=50)):
    server = get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    metrics = get_metrics_history(server_id, limit)
    return {"server": {"id": server["id"], "name": server["name"]}, "metrics": metrics, "count": len(metrics)}


@app.post("/api/servers/{server_id}/metrics", tags=["Métricas"], status_code=status.HTTP_201_CREATED)
async def add_metrics_endpoint(server_id: int, metrics: MetricsCreate):
    server = get_server_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    metrics_data = metrics.model_dump()
    metrics_data["server_id"] = server_id
    metrics_id = add_metrics(metrics_data)
    return {"id": metrics_id, "message": f"Métricas adicionadas para '{server['name']}'"}


@app.get("/api/alerts", tags=["Alertas"])
async def list_alerts():
    alerts = get_active_alerts()
    return {"alerts": alerts, "total": len(alerts)}


@app.post("/api/alerts", tags=["Alertas"], status_code=status.HTTP_201_CREATED)
async def create_alert_endpoint(alert: AlertCreate):
    server = get_server_by_id(alert.server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    alert_id = create_alert(alert)
    return {"id": alert_id, "message": "Alerta criado com sucesso"}


@app.get("/api/search", tags=["Busca"])
async def search_servers(q: str = Query(..., example="web")):
    servers = get_all_servers()
    if q is None or q == "" or q == "*" or q == "all":
        return {"query": q, "results": servers, "count": len(servers)}
    results = [s for s in servers if q.lower() in s["name"].lower() or q in s["ip"]]
    return {"query": q, "results": results, "count": len(results)}


@app.get("/api/stats", tags=["Root"])
async def get_stats():
    servers = get_all_servers()
    alerts = get_active_alerts()
    online = sum(1 for s in servers if s["status"] == "online")
    offline = sum(1 for s in servers if s["status"] == "offline")
    maintenance = sum(1 for s in servers if s["status"] == "maintenance")
    critical = sum(1 for a in alerts if a["severity"] == "critical")
    warning = sum(1 for a in alerts if a["severity"] == "warning")
    info = sum(1 for a in alerts if a["severity"] == "info")
    return {
        "total_servers": len(servers),
        "servers_by_status": {"online": online, "offline": offline, "maintenance": maintenance},
        "active_alerts": len(alerts),
        "alerts_by_severity": {"critical": critical, "warning": warning, "info": info}
    }


# ============================================================
# 4. MAIN
# ============================================================

def run_http_server():
    init_database()
    print("=" * 60)
    print("🚀 MCP Server Hub - API REST (porta 8080)")
    print("=" * 60)
    print(f"📖 Swagger UI:  http://localhost:8080/docs")
    print(f"📚 ReDoc:       http://localhost:8080/redoc")
    print(f"📋 OpenAPI:     http://localhost:8080/openapi.json")
    print("=" * 60)
    print("💡 Pressione CTRL+C para parar o servidor")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    run_http_server()