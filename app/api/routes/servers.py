from fastapi import APIRouter, Depends, Query, status
from app.api.schemas import ServerCreate, ServerResponse
from app.api.application.services import ServerService
from app.api.domain.entities import Server, ServerMetrics
from app.api.domain.enums import ServerStatus
from app.api.container import services
from app.api.schemas import MetricsResponse

router = APIRouter(prefix="/api/servers", tags=["Servers"])


def server_service(dep=Depends(services)) -> ServerService:
    return dep["servers"]

def metrics_to_response(metrics: ServerMetrics | None) -> MetricsResponse | None:
    if metrics is None:
        return None

    if metrics.id is None:
        raise ValueError("Cannot create a response for a server metrics without an id")

    return MetricsResponse(
        id=metrics.id,
        server_id=metrics.server_id,
        cpu_usage_percent=metrics.cpu_usage_percent,
        memory_usage_percent=metrics.memory_usage_percent,
        disk_usage_percent=metrics.disk_usage_percent,
        temperature_celsius=metrics.temperature_celsius,
        uptime_seconds=metrics.uptime_seconds,
        timestamp=metrics.timestamp,
    )

def to_response(server: Server) -> ServerResponse:
    if server.id is None:
        raise ValueError("Cannot create a response for a server without an id")
    
    return ServerResponse(
        id=server.id,
        name=server.name,
        ip=server.ip,
        environment=server.environment,
        status=server.status,
        cpu_cores=server.cpu_cores,
        memory_gb=server.memory_gb,
        disk_gb=server.disk_gb,
        last_updated=server.last_updated,
        created_at=server.created_at,
    )


@router.get("", response_model=dict)
def list_servers(service: ServerService = Depends(server_service)):
    servers = [to_response(s) for s in service.list_servers()]
    return {"servers": servers, "total": len(servers)}


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(server_id: int, dep=Depends(services)):
    server = dep["servers"].get_server(server_id)
    response = to_response(server)
    latest = dep["metrics"].latest(server_id)
    response.metrics = metrics_to_response(latest)
    return response



@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_server_endpoint(payload: ServerCreate, service: ServerService = Depends(server_service)):
    server = service.create_server(Server(**payload.model_dump()))
    return {"id": server.id, "message": f"Servidor '{server.name}' criado com sucesso"}


@router.put("/{server_id}/status", response_model=dict)
def update_status(
    server_id: int,
    server_status: ServerStatus = Query(alias="status"),
    service: ServerService = Depends(server_service),
):
    server = service.update_status(server_id, server_status)
    return {"message": f"Status atualizado para '{server.status.value}'", "server_id": server.id}


@router.delete("/{server_id}", response_model=dict)
def delete_server_endpoint(server_id: int, service: ServerService = Depends(server_service)):
    server = service.get_server(server_id)
    service.delete_server(server_id)
    return {"message": f"Servidor '{server.name}' removido com sucesso"}
