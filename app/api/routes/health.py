from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.infrastructure.persistence.sqlalchemy import engine


router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@router.get("/ready")
def readiness() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
            },
        )

    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
            },
        )