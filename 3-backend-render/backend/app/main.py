"""
NEXUS MEDIA AI — FastAPI Application Entrypoint (Step 3)
Configures structured logging with secret redaction, strict CORS policy,
security headers, rate limiting, safe exception handlers, and all 7 API routers.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    agents,
    analytics,
    articles,
    auth,
    blog,
    health,
    logs,
    news,
    publishing,
    system,
)
from app.config import get_settings
from app.database import dispose_engine
from app.middleware.security_headers import (
    InMemoryRateLimiter,
    RateLimitMiddleware,
    SecretRedactingLogFilter,
    SecurityHeadersMiddleware,
)


def configure_logging() -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger("nexus_media_ai")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactingLogFilter())
        logger.addHandler(handler)
    return logger


logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info("Starting %s (%s) — config=%s", settings.APP_NAME, settings.APP_ENV, settings.redacted_summary())
    yield
    await dispose_engine()
    logger.info("Shutting down %s cleanly.", settings.APP_NAME)


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.APP_NAME,
        description="Autonomous News Intelligence & Publishing Platform — FastAPI Control Backend",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/api/redoc" if settings.APP_ENV != "production" else None,
    )

    # 1. Strict CORS Policy restricted to configured dashboard origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # 2. Security Headers & Rate Limiting Middleware
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        RateLimitMiddleware,
        limiter=InMemoryRateLimiter(
            requests_per_window=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            window_seconds=60,
        ),
    )

    # 3. Safe Global Exception Handlers (no stack traces or secrets leaked)
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request payload failed schema validation.",
                "details": jsonable_encoder(exc.errors()),
                "request_id": request_id,
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error("Unhandled exception on path=%s request_id=%s type=%s", request.url.path, request_id, type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please reference request_id in operator logs.",
                "request_id": request_id,
            },
        )

    # 4. Register all 7 required Step 3 routers
    application.include_router(health.router)
    application.include_router(system.router)
    application.include_router(auth.router)
    application.include_router(agents.router)
    application.include_router(news.router)
    application.include_router(articles.router)
    application.include_router(publishing.router)
    application.include_router(analytics.router)
    application.include_router(logs.router)
    application.include_router(blog.router)

    return application


app = create_app()
