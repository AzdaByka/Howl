"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from sqlalchemy import text

from app.api.errors import http_exception_handler, validation_exception_handler
from app.api.routes import auth, channels, communities, internal, voice
from app.api.websocket.realtime import router as realtime_router
from app.config import settings
from app.infrastructure.database.session import engine
from app.observability import (
    ACTIVE_REQUESTS,
    REQUEST_COUNT,
    REQUEST_DURATION,
    configure_logging,
    request_timer,
)

logger = configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    start = request_timer()
    ACTIVE_REQUESTS.inc()
    try:
        response = await call_next(request)
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_DURATION.labels(request.method, path).observe(request_timer() - start)
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round((request_timer() - start) * 1000, 2),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(communities.router, prefix=settings.api_prefix)
app.include_router(channels.router, prefix=settings.api_prefix)
app.include_router(voice.router, prefix=settings.api_prefix)
app.include_router(realtime_router, prefix=settings.api_prefix)
app.include_router(internal.router)
app.mount("/metrics", make_asgi_app())
