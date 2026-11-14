"""
ServicePulse - Enterprise RMM & ITSM Platform Backend
Author: Muhammadyusuf Usmonov
Academic Purpose: AT-Servis BMI
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.api import api_router
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.base import Base
from backend.app.db.init_db import init_db
from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.services.ws_manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes database tables, default seed data, and real-time outbox listener.
    """
    logger.info("Starting ServicePulse Backend v%s in %s mode...", settings.VERSION, settings.ENVIRONMENT)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as session:
            await init_db(session)
        logger.info("Database schemas and seed data verified successfully.")
    except Exception as exc:
        logger.error("Database startup initialization encountered an issue: %s", exc, exc_info=True)

    outbox_task = asyncio.create_task(ws_manager.start_outbox_listener())

    yield

    logger.info("Shutting down ServicePulse Backend...")
    ws_manager.stop_outbox_listener()
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass

    logger.info("Disposing database engine...")
    await engine.dispose()
    logger.info("ServicePulse Backend shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ServicePulse — Enterprise Remote Monitoring, Management and ITSM Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global unhandled exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing request %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please consult system logs."}
    )

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Top-level direct healthcheck endpoint for load balancers and container probes
@app.get("/health", tags=["health"], summary="Root healthcheck probe")
async def root_health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/", tags=["root"], summary="ServicePulse Welcome Root")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "author": "Muhammadyusuf Usmonov",
        "purpose": "AT-Servis BMI",
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_STR
    }
