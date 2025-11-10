"""Wrapper for Claude Agent SDK with proper typing and error handling."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeAgent:
    """Wrapper around Claude Agent SDK agent."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        working_directory: str,
        allowed_tools: Optional[list[str]] = None,
        skills: Optional[list[str]] = None,
    ):
        """Initialize Claude Agent.

        Args:
            name: Agent identifier
            system_prompt: System prompt defining agent behavior
            working_directory: Agent's workspace directory
            allowed_tools: List of allowed tool names
            skills: List of skill identifiers to load
        """
        self.name = name
        self.system_prompt = system_prompt
        self.working_directory = Path(working_directory)
        self.allowed_tools = allowed_tools or ["read", "write", "bash"]
        self.skills = skills or []

        # Ensure workspace exists
        self.working_directory.mkdir(parents=True, exist_ok=True)

        # Initialize SDK agent
        self._init_sdk_agent()

    def _init_sdk_agent(self):
        """Initialize the actual Claude Agent SDK agent."""
        try:
            from claude_agent_sdk import ClaudeAgent as SDKAgent

            # Create agent configuration
            config = {
                "name": self.name,
                "system_prompt": self.system_prompt,
                "working_directory": str(self.working_directory),
            }

            # Add tool permissions if specified
            if self.allowed_tools:
                config["allowed_tools"] = self.allowed_tools

            # Add skills if specified
            if self.skills:
                config["skills"] = self.skills

            self._agent = SDKAgent(**config)

            logger.info(f"✓ Initialized Claude Agent: {self.name}")
            logger.info(f"  Workspace: {self.working_directory}")
            logger.info(f"  Tools: {self.allowed_tools}")
            logger.info(f"  Skills: {self.skills if self.skills else 'None'}")

        except ImportError as e:
            logger.error("Claude Agent SDK not available")
            logger.error(str(e))
            raise RuntimeError(
                "Claude Agent SDK not installed. "
                "Install with: pip install claude-agent-sdk"
            ) from e

    async def run(self, message: str) -> str:
        """Run agent with a message.

        Args:
            message: Input message for the agent

        Returns:
            Agent's response
        """
        try:
            logger.info(f"Running agent {self.name}...")
            logger.debug(f"Message: {message[:200]}...")

            # Run the agent
            response = await self._agent.run(message)

            logger.info(f"✓ Agent {self.name} completed")
            logger.debug(f"Response: {response[:200]}...")

            return response

        except Exception as e:
            logger.error(f"Agent {self.name} failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup agent resources."""
        try:
            if hasattr(self._agent, "cleanup"):
                await self._agent.cleanup()
            logger.info(f"✓ Cleaned up agent: {self.name}")
        except Exception as e:
            logger.warning(f"Error cleaning up agent {self.name}: {e}")

    def get_workspace_files(self) -> list[Path]:
        """Get list of files in agent's workspace.

        Returns:
            List of file paths
        """
        if not self.working_directory.exists():
            return []

        return list(self.working_directory.rglob("*"))

    def read_workspace_file(self, relative_path: str) -> str:
        """Read a file from agent's workspace.

        Args:
            relative_path: Path relative to workspace

        Returns:
            File contents
        """
        file_path = self.working_directory / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return file_path.read_text()
