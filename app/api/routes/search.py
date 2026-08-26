from fastapi import APIRouter, Depends, Query
from app.api.schemas import ServerSummary
from app.api.container import services

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("", response_model=dict)
def search_servers(q: str = Query(min_length=1, description="Partial server name or IP"), dep=Depends(services)):
    results = [ServerSummary.model_validate(s) for s in dep["servers"].search_servers(q)]
    return {"query": q, "results": results, "count": len(results)}
