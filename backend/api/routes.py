from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

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
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


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
    @router.post("/analyze")
    async def analyze_codebase(request: AnalyzeRequest):
        """Start analyzing a codebase"""
        try:
            # Notify clients that analysis is starting
            await manager.broadcast({
                "type": "analysis_started",
                "data": {"path": request.path}
            })

            # Run analysis (this could take a while)
            system_agent = await orchestrator.analyze_codebase(request.path)

            # Get all cards created during analysis
            cards = await db.get_all_cards()

            # Notify clients that analysis is complete
            await manager.broadcast({
                "type": "analysis_completed",
                "data": {
                    "agent_id": system_agent.id,
                    "cards_count": len(cards)
                }
            })

            return {
                "status": "completed",
                "agent_id": system_agent.id,
                "cards_created": len(cards),
                "hierarchy": await orchestrator.get_agent_hierarchy(system_agent.id)
            }

        except Exception as e:
            await manager.broadcast({
                "type": "analysis_error",
                "data": {"error": str(e)}
            })
            raise HTTPException(status_code=500, detail=str(e))

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
