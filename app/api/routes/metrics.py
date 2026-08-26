from fastapi import APIRouter, Depends, Query, status
from app.api.schemas import MetricsCreate, MetricsResponse
from app.api.domain.entities import ServerMetrics
from app.api.container import services

router = APIRouter(prefix="/api/servers/{server_id}/metrics", tags=["Metrics"])


def deps(dep=Depends(services)):
    return dep


@router.get("", response_model=dict)
def get_metrics(
    server_id: int,
    limit: int = Query(10, ge=1, le=50),
    dep=Depends(deps),
):
    server = dep["servers"].get_server(server_id)
    metrics = dep["metrics"].history(server_id, limit)
    return {
        "server": {"id": server.id, "name": server.name},
        "metrics": [MetricsResponse.model_validate(m) for m in metrics],
        "count": len(metrics),
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_metrics_endpoint(server_id: int, payload: MetricsCreate, dep=Depends(deps)):
    server = dep["servers"].get_server(server_id)
    metrics = dep["metrics"].add(ServerMetrics(server_id=server_id, **payload.model_dump()))
    return {"id": metrics.id, "message": f"Métricas adicionadas para '{server.name}'"}
