"""FastAPI server for Eidolon orchestration UI."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..orchestrator import AgentConfig, AgentMessage, AgentOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Eidolon Orchestrator API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class AppState:
    """Application state."""

    orchestrator: Optional[AgentOrchestrator] = None
    analysis_sessions: dict[str, dict] = {}
    websocket_connections: list[WebSocket] = []
    workspace_base = Path("/tmp/eidolon/ui")

state = AppState()


# API Models
class AnalysisRequest(BaseModel):
    """Request to analyze a file."""

    file_path: str
    complexity_threshold: int = 10
    max_parallel_agents: int = 5


class AgentInfo(BaseModel):
    """Agent information."""

    id: str
    role: str
    status: str
    workspace: str
    message_count: int
    created_at: str


class FindingResponse(BaseModel):
    """Analysis finding."""

    id: str
    severity: str  # critical, high, medium, low
    type: str  # bug, security, performance, style
    description: str
    file_path: str
    line_number: Optional[int]
    suggested_fix: Optional[str]
    agent_id: str


# WebSocket manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")

manager = ConnectionManager()


# API Endpoints
@app.get("/api/status")
async def get_status():
    """Get orchestrator status."""
    return {
        "status": "running" if state.orchestrator else "idle",
        "active_sessions": len(state.analysis_sessions),
        "workspace": str(state.workspace_base),
    }


@app.post("/api/analyze")
async def start_analysis(request: AnalysisRequest):
    """Start analyzing a file."""
    try:
        # Create session
        session_id = str(uuid4())
        session_workspace = state.workspace_base / session_id
        session_workspace.mkdir(parents=True, exist_ok=True)

        # Initialize orchestrator with WebSocket manager
        orchestrator = AgentOrchestrator(base_workspace=session_workspace, ws_manager=manager)
        state.orchestrator = orchestrator

        # Store session
        state.analysis_sessions[session_id] = {
            "id": session_id,
            "file_path": request.file_path,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "findings": [],
        }

        # Broadcast event
        await manager.broadcast({
            "type": "analysis_started",
            "session_id": session_id,
            "file_path": request.file_path,
        })

        # Start analysis in background
        asyncio.create_task(run_analysis(session_id, request, orchestrator, manager))

        return {"session_id": session_id, "status": "started"}

    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get analysis session details."""
    if session_id not in state.analysis_sessions:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    return state.analysis_sessions[session_id]


@app.get("/api/agents")
async def list_agents():
    """List all active agents."""
    if not state.orchestrator:
        return []

    agents = []
    for agent_id, agent in state.orchestrator.agents.items():
        agents.append({
            "id": agent_id,
            "role": agent_id.split("-")[0],
            "status": "active",
            "workspace": str(state.orchestrator.base_workspace / agent_id),
            "message_count": len([m for m in state.orchestrator.message_log if m.from_agent == agent_id]),
            "created_at": datetime.now().isoformat(),
        })

    return agents


@app.get("/api/messages")
async def get_messages(session_id: Optional[str] = None, limit: int = 100):
    """Get message history."""
    if not state.orchestrator:
        return []

    messages = []
    for msg in state.orchestrator.message_log[-limit:]:
        messages.append({
            "id": msg.message_id,
            "timestamp": msg.timestamp.isoformat(),
            "from_agent": msg.from_agent,
            "to_agent": msg.to_agent,
            "content": msg.content[:200],  # Truncate for UI
            "full_content": msg.content,
        })

    return messages


@app.get("/api/findings")
async def get_findings(session_id: Optional[str] = None):
    """Get analysis findings."""
    if session_id and session_id in state.analysis_sessions:
        return state.analysis_sessions[session_id].get("findings", [])

    # Return all findings
    all_findings = []
    for session in state.analysis_sessions.values():
        all_findings.extend(session.get("findings", []))

    return all_findings


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for analysis."""
    try:
        # Save file
        upload_dir = state.workspace_base / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename
        content = await file.read()
        file_path.write_bytes(content)

        logger.info(f"Uploaded file: {file_path}")

        return {
            "file_path": str(file_path),
            "filename": file.filename,
            "size": len(content),
        }

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            logger.debug(f"Received from client: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Background tasks
async def run_analysis(session_id: str, request: AnalysisRequest, orchestrator: AgentOrchestrator, ws_manager):
    """Run analysis in background and stream events."""
    try:
        logger.info(f"Starting analysis for session {session_id}")

        # Read file
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code = file_path.read_text()

        # Extract functions (simplified - would use AST in real impl)
        functions = [("example_function", code)]  # Placeholder

        # Broadcast agent spawning
        logger.info(f"Broadcasting analysis_progress event")
        await ws_manager.broadcast({
            "type": "analysis_progress",
            "session_id": session_id,
            "message": f"Analyzing {len(functions)} functions...",
        })

        # Analyze in parallel
        logger.info(f"Calling orchestrator.analyze_function_parallel with {len(functions)} functions")
        results = await orchestrator.analyze_function_parallel(functions)
        logger.info(f"Got {len(results)} results from orchestrator")

        # Log the actual results for debugging
        for i, result in enumerate(results):
            logger.info(f"Result {i}: {result[:500] if isinstance(result, str) else result}")

        # Process results and extract findings
        findings = []
        for i, result in enumerate(results):
            if isinstance(result, str):
                # Create a finding from the LLM response
                # The LLM response should contain analysis results
                finding = {
                    "id": str(uuid4()),
                    "severity": "high" if any(word in result.lower() for word in ["critical", "error", "bug"]) else
                               "medium" if any(word in result.lower() for word in ["warning", "issue", "problem"]) else "low",
                    "type": "complexity" if "complexity" in result.lower() else
                           "security" if "security" in result.lower() else
                           "performance" if "performance" in result.lower() else
                           "style",
                    "description": result[:200] if len(result) > 200 else result,
                    "file_path": request.file_path,
                    "line_number": None,
                    "agent_id": f"analyzer-{i+1}",
                    "suggested_fix": None,
                }
                findings.append(finding)
                logger.info(f"Created finding: {finding['severity']} - {finding['type']}")

                # Broadcast finding
                await ws_manager.broadcast({
                    "type": "finding_detected",
                    "session_id": session_id,
                    "finding": finding,
                })

        # Update session
        state.analysis_sessions[session_id]["findings"] = findings
        state.analysis_sessions[session_id]["status"] = "completed"

        # Broadcast completion
        logger.info(f"Broadcasting analysis_complete event")
        await ws_manager.broadcast({
            "type": "analysis_complete",
            "session_id": session_id,
            "findings_count": len(findings),
        })

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)

        state.analysis_sessions[session_id]["status"] = "failed"
        state.analysis_sessions[session_id]["error"] = str(e)

        await ws_manager.broadcast({
            "type": "analysis_failed",
            "session_id": session_id,
            "error": str(e),
        })


# Startup
@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    logger.info("Eidolon Orchestrator API starting...")
    state.workspace_base.mkdir(parents=True, exist_ok=True)
    logger.info(f"Workspace: {state.workspace_base}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8181)
