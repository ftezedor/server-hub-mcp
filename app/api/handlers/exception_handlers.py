"""Global FastAPI exception handlers.

Domain exceptions are translated at the HTTP boundary so route handlers do not
need to repeat try/except blocks for expected application errors.
"""


import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.domain.exceptions import (
    DuplicateServerError,
    DomainError,
    ServerNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


_DOMAIN_STATUS_CODES = {
    ServerNotFoundError: 404,
    DuplicateServerError: 409,
    ValidationError: 422,
}


def _domain_status_code(exc: DomainError) -> int:
    for exception_type, status_code in _DOMAIN_STATUS_CODES.items():
        if isinstance(exc, exception_type):
            return status_code

    return 400


async def domain_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, DomainError):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return JSONResponse(
        status_code=_domain_status_code(exc),
        content={"detail": str(exc)},
    )


async def http_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


async def validation_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def unhandled_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled API exception", exc_info=exc)

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )