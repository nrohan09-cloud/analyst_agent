"""
Main FastAPI application for the Analyst Agent service.

Sets up the web server, middleware, routes, and error handling.
"""

from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any
import time
import uuid

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from analyst_agent.settings import settings
from analyst_agent.models.contracts import (
    AnalysisRequest,
    AnalysisResponse,
    JobStatusResponse
)
from analyst_agent.schemas import (
    HealthCheck,
    ErrorResponse,
    JobStatus,
)

# Configure structured logging
logger = structlog.get_logger(__name__)

# Global state for tracking application startup time
app_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global app_start_time
    
    # Startup
    app_start_time = time.time()
    logger.info("Starting Analyst Agent service", version=settings.app_version)
    
    # TODO: Initialize database connections, LLM providers, etc.
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analyst Agent service")
    # TODO: Clean up resources


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Analyst Agent API",
        description="Autonomous AI data analyst/scientist service",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add middleware
    allow_origins = settings.allowed_origins if not settings.debug else ["*"]
    allow_credentials = False if allow_origins == ["*"] else True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Configure LangSmith env if enabled
    if settings.langsmith_tracing:
        import os
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        if settings.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        if settings.langsmith_endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        if settings.langsmith_project:
            os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Allow all hosts for production deployment
        )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="internal_server_error",
                message="An unexpected error occurred",
                timestamp=datetime.utcnow()
            ).dict()
        )
    
    # Include API routes
    from analyst_agent.api.routes import analysis, health
    
    app.include_router(
        health.router,
        prefix=settings.api_prefix,
        tags=["health"]
    )
    
    app.include_router(
        analysis.router,
        prefix=settings.api_prefix,
        tags=["analysis"]
    )
    
    return app


# Create the app instance
app = create_app() 