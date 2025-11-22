from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import asyncio
import os

from models import Card, CardStatus, Agent
from storage import Database
from agents import AgentOrchestrator


# Request/Response models
class AnalyzeRequest(BaseModel):
    path: str


class UpdateCardRequest(BaseModel):
    status: Optional[CardStatus] = None
    routing: Optional[Dict[str, str]] = None


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients, removing dead connections"""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Connection is dead, mark for removal
                dead_connections.append(connection)

        # Clean up dead connections to prevent memory leak
        for conn in dead_connections:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


# Create router and connection manager
router = APIRouter()
manager = ConnectionManager()


def create_routes(db: Database, orchestrator: AgentOrchestrator):
    """Create API routes with database and orchestrator dependencies"""

    # Card endpoints
    @router.get("/cards", response_model=List[Card])
    async def get_cards(
        type: Optional[str] = None,
        status: Optional[str] = None,
        owner_agent: Optional[str] = None
    ):
        """Get all cards with optional filters"""
        filters = {}
        if type:
            filters["type"] = type
        if status:
            filters["status"] = status
        if owner_agent:
            filters["owner_agent"] = owner_agent

        cards = await db.get_all_cards(filters)
        return cards

    @router.get("/cards/{card_id}", response_model=Card)
    async def get_card(card_id: str):
        """Get a specific card"""
        card = await db.get_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        return card

    @router.put("/cards/{card_id}", response_model=Card)
    async def update_card(card_id: str, request: UpdateCardRequest):
        """Update a card"""
        card = await db.get_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        if request.status:
            card.update_status(request.status, actor="user")

        if request.routing:
            card.routing.from_tab = request.routing.get("from_tab")
            card.routing.to_tab = request.routing.get("to_tab")
            card.add_log_entry(
                actor="user",
                event=f"Routed from {card.routing.from_tab} to {card.routing.to_tab}"
            )

        card = await db.update_card(card)

        # Broadcast update
        await manager.broadcast({
            "type": "card_updated",
            "data": card.dict()
        })

        return card

    @router.delete("/cards/{card_id}")
    async def delete_card(card_id: str):
        """Delete a card"""
        await db.delete_card(card_id)
        await manager.broadcast({
            "type": "card_deleted",
            "data": {"id": card_id}
        })
        return {"status": "deleted"}

    # Agent endpoints
    @router.get("/agents", response_model=List[Agent])
    async def get_agents():
        """Get all agents"""
        agents = await db.get_all_agents()
        return agents

    @router.get("/agents/{agent_id}", response_model=Agent)
    async def get_agent(agent_id: str):
        """Get a specific agent (for snoop view)"""
        agent = await db.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent

    @router.get("/agents/{agent_id}/hierarchy")
    async def get_agent_hierarchy(agent_id: str):
        """Get the agent hierarchy tree"""
        hierarchy = await orchestrator.get_agent_hierarchy(agent_id)
        if not hierarchy:
            raise HTTPException(status_code=404, detail="Agent not found")
        return hierarchy

    # Analysis endpoints
    @router.get("/progress")
    def get_progress():
        """Get current analysis progress"""
        return orchestrator.get_progress()

    @router.post("/analyze")
    async def analyze_codebase(request: AnalyzeRequest):
        """Start analyzing a codebase with parallel execution and progress tracking"""
        try:
            # Validate and sanitize the path to prevent path traversal attacks
            try:
                analysis_path = Path(request.path).resolve()

                # Check if path exists
                if not analysis_path.exists():
                    raise HTTPException(status_code=404, detail=f"Path does not exist: {request.path}")

                # Check if it's a directory (we analyze directories, not individual files)
                if not analysis_path.is_dir():
                    raise HTTPException(status_code=400, detail="Path must be a directory")

                # Optional: Restrict to allowed base directories (commented out for flexibility)
                # allowed_base = Path("/home/user").resolve()
                # if not str(analysis_path).startswith(str(allowed_base)):
                #     raise HTTPException(status_code=403, detail="Path outside allowed directory")

            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

            # Notify clients that analysis is starting
            await manager.broadcast({
                "type": "analysis_started",
                "data": {"path": str(analysis_path)}
            })

            # Start a background task to send progress updates
            async def send_progress_updates():
                while True:
                    await asyncio.sleep(2)  # Send updates every 2 seconds
                    progress = orchestrator.get_progress()

                    # Stop if analysis is complete
                    if progress['completed_modules'] >= progress['total_modules']:
                        break

                    await manager.broadcast({
                        "type": "analysis_progress",
                        "data": progress
                    })

            # Start progress updates task (don't await it)
            progress_task = asyncio.create_task(send_progress_updates())

            # Run analysis (this could take a while)
            system_agent = await orchestrator.analyze_codebase(str(analysis_path))

            # Cancel progress updates
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            # Get all cards created during analysis
            cards = await db.get_all_cards()

            # Get final progress with errors
            final_progress = orchestrator.get_progress()

            # Notify clients that analysis is complete
            await manager.broadcast({
                "type": "analysis_completed",
                "data": {
                    "agent_id": system_agent.id,
                    "cards_count": len(cards),
                    "progress": final_progress
                }
            })

            return {
                "status": "completed",
                "agent_id": system_agent.id,
                "cards_created": len(cards),
                "progress": final_progress,
                "hierarchy": await orchestrator.get_agent_hierarchy(system_agent.id)
            }

        except Exception as e:
            await manager.broadcast({
                "type": "analysis_error",
                "data": {"error": str(e)}
            })
            raise HTTPException(status_code=500, detail=str(e))

    # Fix application endpoints
    @router.post("/cards/{card_id}/apply-fix")
    async def apply_fix(card_id: str):
        """Apply a proposed fix to the codebase"""
        card = await db.get_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        if not card.proposed_fix:
            raise HTTPException(status_code=400, detail="Card has no proposed fix")

        if not card.proposed_fix.validated:
            raise HTTPException(
                status_code=400,
                detail=f"Fix has validation errors: {', '.join(card.proposed_fix.validation_errors)}"
            )

        try:
            # Read the current file
            with open(card.proposed_fix.file_path, 'r') as f:
                lines = f.readlines()

            # Create backup
            backup_path = card.proposed_fix.file_path + '.monad_backup'
            with open(backup_path, 'w') as f:
                f.writelines(lines)

            # Replace the lines
            new_lines = (
                lines[:card.proposed_fix.line_start - 1] +
                [card.proposed_fix.fixed_code + '\n'] +
                lines[card.proposed_fix.line_end:]
            )

            # Write back
            with open(card.proposed_fix.file_path, 'w') as f:
                f.writelines(new_lines)

            # Update card status
            card.update_status(CardStatus.DONE, actor="user")
            card.add_log_entry(
                actor="user",
                event=f"Applied fix to {card.proposed_fix.file_path}",
                diff={"backup": backup_path}
            )
            await db.update_card(card)

            # Broadcast update
            await manager.broadcast({
                "type": "fix_applied",
                "data": {
                    "card_id": card_id,
                    "file": card.proposed_fix.file_path,
                    "backup": backup_path
                }
            })

            return {
                "status": "applied",
                "file": card.proposed_fix.file_path,
                "backup": backup_path
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to apply fix: {str(e)}")

    # Cache management endpoints
    @router.get("/cache/stats")
    async def get_cache_stats():
        """Get cache statistics"""
        stats = await orchestrator.get_cache_statistics()
        return stats

    @router.delete("/cache")
    async def clear_cache():
        """Clear the entire analysis cache"""
        deleted = await orchestrator.clear_cache()
        await manager.broadcast({
            "type": "cache_cleared",
            "data": {"deleted_entries": deleted}
        })
        return {"status": "cleared", "deleted_entries": deleted}

    @router.delete("/cache/file")
    async def invalidate_file_cache(file_path: str):
        """Invalidate cache for a specific file"""
        deleted = await orchestrator.invalidate_file_cache(file_path)
        return {"status": "invalidated", "deleted_entries": deleted, "file_path": file_path}

    # WebSocket endpoint
    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket for real-time updates"""
        await manager.connect(websocket)
        try:
            while True:
                # Keep connection alive and receive any client messages
                data = await websocket.receive_text()
                # Echo back or process as needed
                await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    return router
