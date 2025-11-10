"""Agent orchestrator using Claude Agent SDK.

This orchestrator spawns multiple Claude Code agents and mediates
communication between them for full observability.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """A message between agents."""

    timestamp: datetime
    from_agent: str
    to_agent: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class AgentConfig:
    """Configuration for spawning an agent."""

    role: str
    system_prompt: str
    workspace: Path
    allowed_tools: list[str] = field(default_factory=lambda: ["read", "write", "bash"])
    max_tokens: int = 4096


class AgentOrchestrator:
    """Orchestrates multiple Claude Agent SDK agents with full observability."""

    def __init__(self, base_workspace: Path, ws_manager=None):
        """Initialize orchestrator.

        Args:
            base_workspace: Base directory for agent workspaces
            ws_manager: WebSocket manager for broadcasting events (optional)
        """
        self.base_workspace = base_workspace
        self.agents: dict[str, "ClaudeAgent"] = {}
        self.message_log: list[AgentMessage] = []
        self.agent_counter = 0
        self.ws_manager = ws_manager

    async def spawn_agent(self, config: AgentConfig) -> str:
        """Spawn a new Claude Code agent.

        Args:
            config: Agent configuration

        Returns:
            Agent ID
        """
        # Create unique agent ID
        self.agent_counter += 1
        agent_id = f"{config.role}-{self.agent_counter}"

        # Create workspace
        workspace = self.base_workspace / agent_id
        workspace.mkdir(parents=True, exist_ok=True)

        logger.info(f"Spawning agent: {agent_id}")
        logger.info(f"  Role: {config.role}")
        logger.info(f"  Workspace: {workspace}")

        # Use LLM client directly for now (Agent SDK has subprocess issues)
        # TODO: Fix Claude Agent SDK integration (EPIPE errors, ResultMessage not received)
        from ..llm.config import create_llm_from_env

        llm = create_llm_from_env()
        if not llm:
            raise RuntimeError("No LLM client configured")

        agent_data = {
            "id": agent_id,
            "role": config.role,
            "system_prompt": config.system_prompt,
            "workspace": workspace,
            "llm": llm,
            "type": "llm",
        }

        self.agents[agent_id] = agent_data
        logger.info(f"✓ Agent {agent_id} spawned successfully (using LLM client)")

        # Broadcast agent spawned event
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "agent_spawned",
                "agent_id": agent_id,
                "role": config.role,
            })

        return agent_id

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
    ) -> str:
        """Send message from one agent to another.

        Args:
            from_agent: Source agent ID (or "orchestrator")
            to_agent: Target agent ID
            message: Message content

        Returns:
            Agent's response
        """
        # Log outgoing message
        msg = AgentMessage(
            timestamp=datetime.now(),
            from_agent=from_agent,
            to_agent=to_agent,
            content=message,
        )
        self.message_log.append(msg)

        logger.info(f"\n{'='*60}")
        logger.info(f"MESSAGE: {from_agent} → {to_agent}")
        logger.info(f"{'='*60}")
        logger.info(f"{message[:200]}...")

        # Broadcast message sent event
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "message_sent",
                "from": from_agent,
                "to": to_agent,
                "content": message,
            })

        # Send to target agent
        if to_agent not in self.agents:
            raise ValueError(f"Agent {to_agent} not found")

        agent_data = self.agents[to_agent]

        # Handle based on agent type
        if agent_data["type"] == "sdk":
            # Use Claude Agent SDK
            client = agent_data["client"]
            await client.query(message)

            # Collect response messages with timeout
            response_parts = []
            try:
                async with asyncio.timeout(120):  # 2 minute timeout
                    async for msg in client.receive_response():
                        logger.info(f"Received message type: {type(msg).__name__}")

                        # Check for ResultMessage (indicates completion)
                        if msg.__class__.__name__ == 'ResultMessage':
                            logger.info(f"Got ResultMessage, stopping iteration")
                            break

                        # Extract text from AssistantMessage
                        if hasattr(msg, "content"):
                            for block in msg.content:
                                if hasattr(block, "text"):
                                    response_parts.append(block.text)
                                    logger.info(f"Added text block: {block.text[:100]}...")
                        elif hasattr(msg, "text"):
                            response_parts.append(msg.text)
                            logger.info(f"Added text: {msg.text[:100]}...")

            except TimeoutError:
                logger.warning(f"Agent {to_agent} response timed out after 120s")
                response = "Agent timed out - no response received"
                return response
            except Exception as e:
                logger.error(f"Error receiving response from agent {to_agent}: {e}", exc_info=True)
                response = f"Agent error: {str(e)}"
                return response

            response = "\n".join(response_parts) if response_parts else "No response from agent"
            logger.info(f"Collected {len(response_parts)} response parts, total length: {len(response)}")

        else:
            # Use LLM client fallback
            llm = agent_data["llm"]
            system_prompt = agent_data["system_prompt"]
            full_prompt = f"{system_prompt}\n\n{message}"
            response = await llm.complete(full_prompt)

        # Log response
        response_msg = AgentMessage(
            timestamp=datetime.now(),
            from_agent=to_agent,
            to_agent=from_agent,
            content=response,
        )
        self.message_log.append(response_msg)

        logger.info(f"\nRESPONSE from {to_agent}:")
        logger.info(f"{response[:200]}...")

        # Broadcast response message event
        if self.ws_manager:
            await self.ws_manager.broadcast({
                "type": "message_sent",
                "from": to_agent,
                "to": from_agent,
                "content": response,
            })

        return response

    async def analyze_function_parallel(
        self,
        functions: list[tuple[str, str]],  # (name, code)
    ) -> list[dict]:
        """Analyze multiple functions in parallel.

        Args:
            functions: List of (function_name, function_code) tuples

        Returns:
            List of analysis results
        """
        logger.info(f"\n🔍 Analyzing {len(functions)} functions in parallel...")

        # Spawn analyzer agents
        agent_ids = []
        for i, (name, _) in enumerate(functions):
            config = AgentConfig(
                role="analyzer",
                system_prompt=self.get_analyzer_prompt(),
                workspace=self.base_workspace / f"analyzer-{i}",
            )
            agent_id = await self.spawn_agent(config)
            agent_ids.append(agent_id)

        # Analyze in parallel
        tasks = [
            self.send_message(
                from_agent="orchestrator",
                to_agent=agent_id,
                message=f"Analyze this function:\n\nName: {name}\n\nCode:\n{code}",
            )
            for agent_id, (name, code) in zip(agent_ids, functions)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"✓ Completed {len(results)} analyses")
        return results

    async def refactor_with_verification(
        self,
        function_name: str,
        function_code: str,
        complexity: int,
    ) -> dict:
        """Refactor a function with test-based verification.

        Args:
            function_name: Name of function
            function_code: Function source code
            complexity: Measured complexity

        Returns:
            Refactoring result with verification status
        """
        logger.info(f"\n🔧 Refactoring {function_name} (complexity: {complexity})")

        # Spawn refactorer agent
        refactorer_config = AgentConfig(
            role="refactorer",
            system_prompt=self.get_refactoring_prompt(),
            workspace=self.base_workspace / f"refactor-{function_name}",
        )
        refactorer_id = await self.spawn_agent(refactorer_config)

        # Send refactoring task
        refactoring_request = f"""Refactor this complex function using TDD:

Function: {function_name}
Complexity: {complexity}

Code:
```python
{function_code}
```

Steps:
1. Generate pytest tests that capture current behavior
2. Run tests on original function (save to tests/test_original.py)
3. Plan refactoring into 2-4 sub-functions
4. Generate refactored version (save to refactored.py)
5. Run tests on refactored version
6. Compare outputs - if they match, return refactored code
7. If tests fail, iterate and fix until they pass

Save all intermediate results to files for inspection.
"""

        refactored = await self.send_message(
            from_agent="orchestrator",
            to_agent=refactorer_id,
            message=refactoring_request,
        )

        logger.info(f"✓ Refactoring complete for {function_name}")

        return {
            "function_name": function_name,
            "original_complexity": complexity,
            "refactored_code": refactored,
            "agent_id": refactorer_id,
            "workspace": str(self.base_workspace / f"refactor-{function_name}"),
        }

    def get_analyzer_prompt(self) -> str:
        """Get system prompt for analyzer agents."""
        return """You are a code complexity analyzer.

Analyze the given Python function and return JSON with:
{
  "complexity": <cyclomatic complexity>,
  "lines_of_code": <LOC>,
  "parameters": <parameter count>,
  "nesting_depth": <max nesting>,
  "code_smells": ["list", "of", "issues"]
}

Use Python's AST module to measure complexity accurately.
Flag complexity > 10 as high.
"""

    def get_refactoring_prompt(self) -> str:
        """Get system prompt for refactoring agents."""
        return """You are a refactoring expert using Test-Driven Development.

When refactoring:
1. Write pytest tests FIRST that capture current behavior
2. Run tests on original code to ensure they pass
3. Plan refactoring into smaller sub-functions
4. Generate refactored code
5. Run tests on refactored code
6. Iterate until all tests pass

CRITICAL: Use bash to actually RUN the tests. Don't rely on judgment.

Save all files:
- tests/test_behavior.py - Behavior tests
- original.py - Original function
- refactored.py - Refactored version
- test_results.txt - Test execution results

Only return success when tests pass on both versions with identical outputs.
"""

    def export_conversation(self, output_path: Path):
        """Export conversation log to JSON.

        Args:
            output_path: Path to save JSON file
        """
        import json

        data = {
            "messages": [
                {
                    "timestamp": msg.timestamp.isoformat(),
                    "from": msg.from_agent,
                    "to": msg.to_agent,
                    "content": msg.content,
                    "id": msg.message_id,
                }
                for msg in self.message_log
            ],
            "agents": list(self.agents.keys()),
            "total_messages": len(self.message_log),
        }

        output_path.write_text(json.dumps(data, indent=2))
        logger.info(f"✓ Exported conversation to {output_path}")

    async def cleanup(self):
        """Cleanup agent resources."""
        for agent_id, agent in self.agents.items():
            logger.info(f"Cleaning up agent: {agent_id}")
            # Cleanup if SDK provides method
            if hasattr(agent, "cleanup"):
                await agent.cleanup()
