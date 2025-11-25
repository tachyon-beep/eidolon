from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import asyncio
import os
import time

from eidolon.models import Card, CardStatus, CardType, CardPriority, Agent, CardIssue
from eidolon.storage import Database
from eidolon.agents import AgentOrchestrator
from eidolon.business_analyst import BusinessAnalyst
from eidolon.request_context import analysis_registry, AnalysisCancelledError
from eidolon.metrics import (
    track_analysis, http_requests_total, http_request_duration_seconds,
    http_requests_in_progress, websocket_connections_active,
    websocket_messages_total, active_analyses
)
from eidolon.logging_config import get_logger

logger = get_logger(__name__)


# Request/Response models
class AnalyzeRequest(BaseModel):
    path: str


class IncrementalAnalyzeRequest(BaseModel):
    path: str
    base: Optional[str] = None  # Git reference to compare against (branch/commit)


class UpdateCardRequest(BaseModel):
    status: Optional[CardStatus] = None
    routing: Optional[Dict[str, str]] = None
    issues: Optional[List[Dict[str, Any]]] = None


class CreateCardRequest(BaseModel):
    type: CardType
    title: str
    summary: str = ""
    status: CardStatus = CardStatus.NEW
    priority: CardPriority = CardPriority.P2
    owner_agent: Optional[str] = None
    parent: Optional[str] = None
    routing: Optional[Dict[str, str]] = None
    links: Optional[Dict[str, List[str]]] = None
    payload_issue_index: Optional[int] = None  # optional pointer to mark parent issue as promoted


class ReviewCardRequest(BaseModel):
    include_callers: bool = False
    include_callees: bool = False
    include_peers: bool = False


class BAProjectRequest(BaseModel):
    project_name: str
    description: str
    goals: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    assumptions: Optional[List[str]] = None
    path: str


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        websocket_connections_active.set(len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        websocket_connections_active.set(len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients, removing dead connections"""
        dead_connections = []
        msg_type = message.get('type', 'unknown')

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                websocket_messages_total.labels(direction='sent', type=msg_type).inc()
            except Exception as e:
                # Connection is dead, mark for removal
                dead_connections.append(connection)

        # Clean up dead connections to prevent memory leak
        for conn in dead_connections:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

        if dead_connections:
            websocket_connections_active.set(len(self.active_connections))


# Create router and connection manager
router = APIRouter()
manager = ConnectionManager()


def create_routes(db: Database, orchestrator: AgentOrchestrator):
    """Create API routes with database and orchestrator dependencies"""
    ba = BusinessAnalyst(llm_provider=orchestrator.llm_provider)

    # Card endpoints
    @router.post("/cards", response_model=Card)
    async def create_card(request: CreateCardRequest):
        """Create a new card (promotion from recommendation or manual)"""
        card = Card(
            id="",
            type=request.type,
            title=request.title,
            summary=request.summary,
            status=request.status,
            priority=request.priority,
            owner_agent=request.owner_agent,
            parent=request.parent
        )

        if request.links:
            card.links.code = request.links.get("code", [])
            card.links.tests = request.links.get("tests", [])
            card.links.docs = request.links.get("docs", [])

        if request.routing:
            card.routing.from_tab = request.routing.get("from_tab")
            card.routing.to_tab = request.routing.get("to_tab")

        card = await db.create_card(card)

        # Link to parent card if provided
        if request.parent:
            parent_card = await db.get_card(request.parent)
            if parent_card:
                if card.id not in parent_card.children:
                    parent_card.children.append(card.id)
                    # If parent has issues, try to mark matching issue as promoted
                    if request.payload_issue_index is not None and 0 <= request.payload_issue_index < len(parent_card.issues):
                        parent_card.issues[request.payload_issue_index].promoted = True
                    await db.update_card(parent_card)
                # Broadcast parent update
                await manager.broadcast({
                    "type": "card_updated",
                    "data": parent_card.dict()
                })

        await manager.broadcast({
            "type": "card_updated",
            "data": card.dict()
        })

        return card

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

        # Support issue updates (e.g., mark promoted)
        if request.issues is not None:
            try:
                card.issues = [CardIssue(**issue) for issue in request.issues]
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid issues payload")

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

    @router.post("/ba/projects")
    async def create_project_from_ba(request: BAProjectRequest):
        """
        Start a Business Architect session to turn a project idea into requirement cards.
        Returns generated cards (not persisted) so the user can promote/save as needed.
        """
        # Validate path
        try:
            project_path = Path(request.path).expanduser().resolve()
            if not project_path.exists() or not project_path.is_dir():
                raise HTTPException(status_code=400, detail=f"Path does not exist or is not a directory: {request.path}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {e}")

        prompt = f"""Project: {request.project_name}
Description: {request.description}
Goals: {request.goals or []}
Constraints: {request.constraints or []}
Assumptions: {request.assumptions or []}
Working path: {project_path}

Produce a small set of requirement/feature cards with:
- title
- summary
- priority (P0-P3)
- acceptance criteria bullets
Return JSON: {{"cards": [{{"title": "...", "summary": "...", "priority": "P1", "acceptance": ["..."]}}]}}"""

        try:
            response = await orchestrator.llm_provider.create_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            import json
            data = json.loads(response.content)
            cards_payload = data.get("cards", []) if isinstance(data, dict) else []
            generated_cards = []
            for idx, c in enumerate(cards_payload):
                title = c.get("title") or f"{request.project_name} feature {idx+1}"
                summary = c.get("summary") or ""
                priority = c.get("priority") or "P2"
                acceptance = c.get("acceptance") or []
                summary_full = summary
                if acceptance:
                    summary_full += "\n\nAcceptance:\n- " + "\n- ".join(acceptance)
                generated_cards.append({
                    "title": title,
                    "summary": summary_full,
                    "priority": priority,
                    "type": "Requirement",
                    "status": "New"
                })
            return {"cards": generated_cards}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"BA generation failed: {e}")

    @router.post("/cards/{card_id}/review")
    async def review_card(card_id: str, request: ReviewCardRequest):
        """
        Send a card back to LLM for review with optional context.
        Supports function/class/module cards with graph context.
        """
        card = await db.get_card(card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        # Try to resolve context from owner agent first, fall back to code links
        file_path: Optional[Path] = None
        target_name: Optional[str] = None
        agent_scope = None

        agent = None
        if card.owner_agent:
            agent = await db.get_agent(card.owner_agent)
            if agent:
                agent_scope = agent.scope
                target_parts = agent.target.split("::")
                if target_parts:
                    file_path = Path(target_parts[0])
                    target_name = target_parts[1] if len(target_parts) > 1 else None

        # Fallback to first code link if no owner agent context
        if (not file_path or not file_path.exists()) and card.links.code:
            candidate = card.links.code[0]
            file_part = candidate.split(":", 1)[0]
            candidate_path = Path(file_part)
            if candidate_path.exists():
                file_path = candidate_path
                target_name = None  # unknown

        if not file_path or not file_path.exists():
            raise HTTPException(status_code=400, detail="Unable to resolve file for review (no owner agent target or code link)")

        from eidolon.analysis import CodeAnalyzer
        analyzer = CodeAnalyzer()
        analyzer.base_path = file_path.parent
        try:
            modules = analyzer.analyze_directory()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to analyze directory for review: {e}")

        module_info = next((m for m in modules if Path(m.file_path).samefile(file_path)), None)
        call_graph = analyzer.build_call_graph(modules)

        context_parts = [
            "Review this card and the associated code element.",
            f"Card title: {card.title}",
            f"Card summary: {card.summary}",
            f"File: {file_path}"
        ]
        if agent_scope:
            context_parts.append(f"Agent scope: {agent_scope}")
        if card.metrics.grade:
            context_parts.append(f"Prior grade: {card.metrics.grade}")

        source_snippet = ""
        func_match = None

        if target_name and module_info:
            # Try to find function or method in module_info
            func_match = next((f for f in module_info.functions if f.name == target_name or target_name.endswith(f.name)), None)
            if not func_match:
                # Check methods with class prefix
                for cls in module_info.classes:
                    for method in cls.methods:
                        combined = f"{cls.name}.{method.name}"
                        if combined == target_name or target_name.endswith(combined):
                            func_match = method
                            break
                    if func_match:
                        break

        if func_match and module_info:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            source_snippet = ''.join(lines[func_match.line_start - 1:func_match.line_end])
            context_parts.append(f"Function lines {func_match.line_start}-{func_match.line_end}:\n```python\n{source_snippet}\n```")

            func_context = analyzer.get_function_context(func_match, call_graph, module_info)
            if request.include_callers and func_context.get('caller_code'):
                context_parts.append("Callers:")
                for caller in func_context['caller_code']:
                    context_parts.append(f"\n```python\n# {caller['name']}\n{caller['code']}\n```")
            if request.include_callees and func_context.get('callee_code'):
                context_parts.append("Callees:")
                for callee in func_context['callee_code']:
                    context_parts.append(f"\n```python\n# {callee['name']}\n{callee['code']}\n```")

            if request.include_peers and module_info.classes:
                # Peer methods in same class if applicable
                peer_methods = []
                for cls in module_info.classes:
                    for method in cls.methods:
                        combined = f"{cls.name}.{method.name}"
                        if combined == target_name:
                            peer_methods = [m for m in cls.methods if m.name != method.name]
                            break
                    if peer_methods:
                        break
                if peer_methods:
                    context_parts.append("Peer methods (same class):")
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                    for peer in peer_methods[:3]:
                        peer_code = ''.join(lines[peer.line_start - 1:peer.line_end])
                        context_parts.append(f"\n```python\n# {peer.name}\n{peer_code}\n```")
        else:
            # Fallback: include whole module snippet
            with open(file_path, 'r') as f:
                context_parts.append(f"Module code:\n```python\n{f.read()[:2000]}\n```")

        prompt = "\n\n".join(context_parts) + "\n\n" + "Provide a concise review: grade the element (A/B/C/D/E), list issues as bullet points, and suggest fixes. Return markdown."

        try:
            llm_response = await orchestrator.llm_provider.create_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM review failed: {str(e)}")

        # Log the review on the card
        card.add_log_entry(
            actor="llm-review",
            event="LLM review requested",
            diff={
                "include_callers": request.include_callers,
                "include_callees": request.include_callees,
                "include_peers": request.include_peers,
                "response_preview": llm_response.content[:2000]
            }
        )
        await db.update_card(card)

        await manager.broadcast({
            "type": "card_updated",
            "data": card.dict()
        })

        return {
            "status": "completed",
            "response": llm_response.content
        }

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

            # Set up activity callback for real-time updates
            async def activity_callback(activity):
                await manager.broadcast({
                    "type": "activity_update",
                    "data": activity
                })

            orchestrator.set_activity_callback(activity_callback)

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

    @router.post("/analyze/incremental")
    async def analyze_incremental(request: IncrementalAnalyzeRequest):
        """Start incremental analysis - only analyze files that changed since last analysis or base commit"""
        try:
            # Validate and sanitize the path to prevent path traversal attacks
            try:
                analysis_path = Path(request.path).resolve()

                # Check if path exists
                if not analysis_path.exists():
                    raise HTTPException(status_code=404, detail=f"Path does not exist: {request.path}")

                # Check if it's a directory
                if not analysis_path.is_dir():
                    raise HTTPException(status_code=400, detail="Path must be a directory")

            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

            # Notify clients that incremental analysis is starting
            await manager.broadcast({
                "type": "analysis_started",
                "data": {
                    "path": str(analysis_path),
                    "mode": "incremental",
                    "base": request.base
                }
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

            # Run incremental analysis
            result = await orchestrator.analyze_incremental(str(analysis_path), base=request.base)

            # Cancel progress updates
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            # Check if there was an error (e.g., not a git repo)
            if 'error' in result:
                await manager.broadcast({
                    "type": "analysis_error",
                    "data": {
                        "error": result['error'],
                        "suggestion": result.get('suggestion', '')
                    }
                })
                raise HTTPException(status_code=400, detail=result['error'])

            # Get all cards created during analysis
            cards = await db.get_all_cards()

            # Notify clients that incremental analysis is complete
            await manager.broadcast({
                "type": "analysis_completed",
                "data": {
                    "mode": "incremental",
                    "session_id": result['session_id'],
                    "stats": result['stats'],
                    "cards_count": len(cards)
                }
            })

            return {
                "status": "completed",
                "mode": "incremental",
                "session_id": result['session_id'],
                "stats": result['stats'],
                "cards_created": len(cards),
                "git_info": result.get('git_info', {}),
                "hierarchy": result.get('hierarchy')
            }

        except HTTPException:
            raise  # Re-raise HTTP exceptions
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
            backup_path = card.proposed_fix.file_path + '.eidolon_backup'
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
                    "backup": backup_path,
                    "diff": {
                        "line_start": card.proposed_fix.line_start,
                        "line_end": card.proposed_fix.line_end,
                        "fixed_code": card.proposed_fix.fixed_code
                    }
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

    # Analysis management endpoints
    @router.get("/analyses/active")
    async def get_active_analyses():
        """Get all currently active analyses"""
        analyses = await analysis_registry.get_all_active()

        # Update metric
        active_analyses.set(len(analyses))

        return {
            "active_count": len(analyses),
            "analyses": analyses
        }

    @router.delete("/analyses/{session_id}")
    async def cancel_analysis(session_id: str):
        """Cancel a running analysis"""
        success = await analysis_registry.cancel(
            session_id,
            reason="User requested cancellation via API"
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Analysis session {session_id} not found")

        logger.info("analysis_cancelled_via_api", session_id=session_id)

        # Broadcast cancellation to WebSocket clients
        await manager.broadcast({
            "type": "analysis_cancelled",
            "data": {"session_id": session_id}
        })

        return {
            "status": "cancelled",
            "session_id": session_id,
            "message": "Analysis cancellation requested"
        }

    @router.get("/analyses/{session_id}/status")
    async def get_analysis_status(session_id: str):
        """Get status of a specific analysis"""
        context = await analysis_registry.get(session_id)

        if not context:
            raise HTTPException(status_code=404, detail=f"Analysis session {session_id} not found")

        return context.get_status()

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
