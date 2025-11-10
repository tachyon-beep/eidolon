"""Per-agent interface to memory store."""

from datetime import datetime
from typing import Optional

from ..agents.models import Analysis, Correction, Question
from .store import AnalysisRecord, MemoryStore


class AgentMemory:
    """Persistent memory for a single agent."""

    def __init__(self, agent_id: str, store: MemoryStore):
        """Initialize agent memory.

        Args:
            agent_id: Unique agent identifier
            store: Underlying memory store
        """
        self.agent_id = agent_id
        self.store = store

    async def record_analysis(self, analysis: Analysis) -> int:
        """Store an analysis.

        Args:
            analysis: Analysis to store

        Returns:
            ID of stored analysis
        """
        return await self.store.save_analysis(self.agent_id, analysis)

    async def get_analyses(
        self,
        commit_sha: Optional[str] = None,
        after: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AnalysisRecord]:
        """Retrieve past analyses.

        Args:
            commit_sha: Optional filter by commit
            after: Optional filter by timestamp
            limit: Maximum number to return

        Returns:
            List of analyses
        """
        return await self.store.get_analyses(
            agent_id=self.agent_id,
            commit_sha=commit_sha,
            after=after,
            limit=limit,
        )

    async def record_conversation(
        self,
        question: Question,
        response: str,
        related_analysis_ids: Optional[list[int]] = None,
    ) -> int:
        """Store agent conversation.

        Args:
            question: Question asked
            response: Agent's response
            related_analysis_ids: Related analyses

        Returns:
            ID of stored conversation
        """
        return await self.store.save_conversation(
            agent_id=self.agent_id,
            from_agent=question.from_agent,
            from_human=question.from_human,
            message=question.text,
            response=response,
            context=question.context,
            related_analysis_ids=related_analysis_ids or [],
        )

    async def record_correction(
        self, original_analysis_id: int, correction: Correction
    ) -> int:
        """Record when agent corrects previous analysis.

        Args:
            original_analysis_id: Original analysis being corrected
            correction: Correction details

        Returns:
            ID of stored correction
        """
        return await self.store.save_correction(
            agent_id=self.agent_id,
            original_analysis_id=original_analysis_id,
            correction=correction,
        )
