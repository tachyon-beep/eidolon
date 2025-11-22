import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from storage import Database
from agents import AgentOrchestrator
from api import create_routes


# Create FastAPI app
app = FastAPI(
    title="MONAD API",
    description="Hierarchical Agent System for Code Analysis",
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


@app.on_event("startup")
async def startup():
    """Initialize database and orchestrator on startup"""
    global db, orchestrator

    db = Database("monad.db")
    await db.connect()

    orchestrator = AgentOrchestrator(db)

    # Create and include routes
    router = create_routes(db, orchestrator)
    app.include_router(router, prefix="/api")


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown"""
    if db:
        await db.close()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MONAD",
        "version": "0.1.0",
        "description": "Recursive unity made manifest."
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
