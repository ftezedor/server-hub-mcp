from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.infrastructure.persistence.sqlalchemy import init_database
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.domain.exceptions import DomainError

from app.api.routes import (
    alerts_router,
    metrics_router,
    search_router,
    servers_router,
    stats_router,
    health_router,
)

from app.api.handlers.exception_handlers import (
    domain_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)



tags_metadata = [
    {"name": "Root", "description": "Informações gerais da API"},
    {"name": "Servers", "description": "Operações de gerenciamento de servidores"},
    {"name": "Metrics", "description": "Coleta e histórico de métricas"},
    {"name": "Alerts", "description": "Gerenciamento de alertas do sistema"},
    {"name": "Search", "description": "Pesquisa de servidores"},
    {"name": "System", "description": "Estatísticas agregadas do sistema"},
    {"name": "Health", "description": "Status de saída do sistema"},
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="Server Hub API",
    version="3.0.0",
    description="Database-independent REST API for Server Hub.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.add_exception_handler(DomainError, domain_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(servers_router)
app.include_router(metrics_router)
app.include_router(alerts_router)
app.include_router(search_router)
app.include_router(stats_router)
app.include_router(health_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Server Hub API",
        "status": "running",
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
    }
