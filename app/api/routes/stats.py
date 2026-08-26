from fastapi import APIRouter, Depends
from app.api.container import services

router = APIRouter(prefix="/api/stats", tags=["System"])


@router.get("")
def get_stats(dep=Depends(services)):
    return dep["system"].stats()
