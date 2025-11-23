import os
import sys
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from eidolon.storage import Database
from eidolon.agents import AgentOrchestrator
from eidolon.api import create_routes
from eidolon.logging_config import configure_logging, get_logger
from eidolon.health import HealthChecker
from eidolon.metrics import get_metrics_response
from eidolon.request_context import analysis_registry

# Configure logging at startup
configure_logging(
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    json_logs=os.environ.get("JSON_LOGS", "false").lower() == "true"
)

logger = get_logger(__name__)


# Create FastAPI app
app = FastAPI(
    title="Eidolon API",
    description="Hierarchical AI Agent System for Code Analysis",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db: Database = None
orchestrator: AgentOrchestrator = None
health_checker: HealthChecker = None


@app.on_event("startup")
async def startup():
    """Initialize database and orchestrator on startup"""
    global db, orchestrator, health_checker

    logger.info("application_startup", version="0.1.0")

    # Initialize database
    logger.info("initializing_database", path="eidolon.db")
    db = Database("eidolon.db")
    await db.connect()
    logger.info("database_connected")

    # Initialize orchestrator
    logger.info("initializing_orchestrator")
    orchestrator = AgentOrchestrator(db)
    await orchestrator.initialize()  # Initialize cache and other async components
    logger.info("orchestrator_initialized", cache_enabled=orchestrator.enable_cache)

    # Initialize health checker
    health_checker = HealthChecker(db, orchestrator.cache)
    logger.info("health_checker_initialized")

    # Create and include routes
    router = create_routes(db, orchestrator)
    app.include_router(router, prefix="/api")

    logger.info("application_ready", message="Eidolon is ready to accept requests")


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    logger.info("application_shutdown", message="Shutting down gracefully")

    # Cancel all active analyses
    logger.info("cancelling_active_analyses")
    await analysis_registry.cancel_all(reason="System shutdown")

    if db:
        logger.info("closing_database")
        await db.close()
        logger.info("database_closed")

    logger.info("application_stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Eidolon",
        "version": "0.1.0",
        "description": "Recursive unity made manifest."
    }


@app.get("/health")
async def health():
    """Comprehensive health check endpoint"""
    if health_checker is None:
        return {
            "status": "initializing",
            "message": "System is starting up"
        }

    return await health_checker.get_health_status()


@app.get("/health/ready")
async def readiness():
    """Readiness probe for Kubernetes/load balancers"""
    if health_checker is None:
        return {"ready": False, "reason": "initializing"}

    return await health_checker.get_readiness()


@app.get("/health/live")
async def liveness():
    """Liveness probe for Kubernetes"""
    return await health_checker.get_liveness() if health_checker else {"alive": True}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format for scraping.
    """
    content, content_type = get_metrics_response()
    return Response(content=content, media_type=content_type)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
