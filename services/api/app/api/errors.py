"""Consistent API exceptions and error responses."""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message, "details": details or {}},
        )


def _response(request: Request, status_code: int, error: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "request_id": getattr(request.state, "request_id", None)},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        error = exc.detail
    else:
        error = {"code": "http_error", "message": str(exc.detail), "details": {}}
    return _response(request, exc.status_code, error)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _response(
        request,
        422,
        {
            "code": "validation_error",
            "message": "Request validation failed",
            "details": {"errors": exc.errors()},
        },
    )
