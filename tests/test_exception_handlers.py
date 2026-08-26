from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.domain.exceptions import (
    DuplicateServerError,
    ServerNotFoundError,
    ValidationError,
)
from app.api.handlers.exception_handlers import (
    domain_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def create_test_app() -> FastAPI:
    app = FastAPI()

    app.add_exception_handler(
        ServerNotFoundError,
        domain_exception_handler,
    )
    app.add_exception_handler(
        DuplicateServerError,
        domain_exception_handler,
    )
    app.add_exception_handler(
        ValidationError,
        domain_exception_handler,
    )
    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )

    @app.get("/not-found")
    def not_found():
        raise ServerNotFoundError("missing")

    @app.get("/duplicate")
    def duplicate():
        raise DuplicateServerError("existing")

    @app.get("/validation")
    def validation():
        raise ValidationError("Invalid request")

    @app.get("/http-error")
    def http_error():
        raise StarletteHTTPException(
            status_code=418,
            detail="I'm a teapot",
        )

    @app.get("/request-validation/{value}")
    def request_validation(value: int):
        return {"value": value}

    @app.get("/unhandled")
    def unhandled():
        raise RuntimeError("internal failure")

    return app


client = TestClient(
    create_test_app(),
    raise_server_exceptions=False,
)


def test_server_not_found_returns_404():
    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Server 'missing' not found"
    }


def test_duplicate_server_returns_409():
    response = client.get("/duplicate")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Server 'existing' already exists"
    }


def test_domain_validation_error_returns_422():
    response = client.get("/validation")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Invalid request"
    }


def test_http_exception_preserves_status_and_detail():
    response = client.get("/http-error")

    assert response.status_code == 418
    assert response.json() == {
        "detail": "I'm a teapot"
    }


def test_request_validation_error_returns_422():
    response = client.get("/request-validation/not-an-integer")

    assert response.status_code == 422

    body = response.json()

    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert body["detail"]


def test_unhandled_exception_returns_generic_500():
    response = client.get("/unhandled")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error"
    }