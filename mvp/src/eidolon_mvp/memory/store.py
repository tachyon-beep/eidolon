"""Persistent storage for agent memories using Postgres."""

import json
from datetime import datetime
from typing import Any, Optional

import psycopg
from psycopg_pool import AsyncConnectionPool

from ..agents.models import Analysis, Correction


class AnalysisRecord:
    """Database record for an analysis."""

    def __init__(
        self,
        id: int,
        agent_id: str,
        timestamp: datetime,
        commit_sha: str,
        trigger: str,
        findings: list[dict],
        reasoning: str,
        confidence: float,
        llm_prompt: Optional[str],
        llm_response: Optional[str],
        metadata: dict,
        was_correct: bool,
    ):
        self.id = id
        self.agent_id = agent_id
        self.timestamp = timestamp
        self.commit_sha = commit_sha
        self.trigger = trigger
        self.findings = findings
        self.reasoning = reasoning
        self.confidence = confidence
        self.llm_prompt = llm_prompt
        self.llm_response = llm_response
        self.metadata = metadata
        self.was_correct = was_correct


class MemoryStore:
    """Persistent storage for agent memories."""

    def __init__(self, dsn: str, pool_size: int = 10):
        """Initialize memory store.

        Args:
            dsn: PostgreSQL connection string
            pool_size: Connection pool size
        """
        self.dsn = dsn
        self.pool: Optional[AsyncConnectionPool] = None
        self.pool_size = pool_size

    async def connect(self):
        """Initialize connection pool."""
        self.pool = AsyncConnectionPool(
            self.dsn,
            min_size=1,
            max_size=self.pool_size,
            open=True,
        )

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def ensure_agent_exists(self, agent_id: str, agent_type: str, scope: dict):
        """Ensure agent is registered in database.

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent (function, module, etc.)
            scope: Scope information as JSON
        """
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_memories (agent_id, agent_type, scope)
                VALUES (%s, %s, %s)
                ON CONFLICT (agent_id) DO NOTHING
                """,
                (agent_id, agent_type, json.dumps(scope)),
            )

    async def save_analysis(self, agent_id: str, analysis: Analysis) -> int:
        """Store an analysis.

        Args:
            agent_id: Agent that performed the analysis
            analysis: Analysis to store

        Returns:
            ID of stored analysis
        """
        async with self.pool.connection() as conn:
            result = await conn.execute(
                """
                INSERT INTO agent_analyses
                (agent_id, timestamp, commit_sha, trigger, findings, reasoning,
                 confidence, llm_prompt, llm_response, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    agent_id,
                    analysis.timestamp,
                    analysis.commit_sha,
                    analysis.trigger,
                    json.dumps([f.to_dict() for f in analysis.findings]),
                    analysis.reasoning,
                    analysis.confidence,
                    analysis.llm_prompt,
                    analysis.llm_response,
                    json.dumps(analysis.metadata),
                ),
            )
            row = await result.fetchone()
            return row[0]

    async def get_analyses(
        self,
        agent_id: str,
        commit_sha: Optional[str] = None,
        after: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AnalysisRecord]:
        """Retrieve analyses for an agent.

        Args:
            agent_id: Agent to query
            commit_sha: Optional filter by commit
            after: Optional filter by timestamp
            limit: Maximum number to return

        Returns:
            List of analysis records
        """
        query = """
            SELECT id, agent_id, timestamp, commit_sha, trigger, findings,
                   reasoning, confidence, llm_prompt, llm_response, metadata,
                   was_correct
            FROM agent_analyses
            WHERE agent_id = %s
        """
        params: list[Any] = [agent_id]

        if commit_sha:
            query += " AND commit_sha = %s"
            params.append(commit_sha)

        if after:
            query += " AND timestamp > %s"
            params.append(after)

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        async with self.pool.connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            return [
                AnalysisRecord(
                    id=row[0],
                    agent_id=row[1],
                    timestamp=row[2],
                    commit_sha=row[3],
                    trigger=row[4],
                    findings=row[5],
                    reasoning=row[6],
                    confidence=row[7],
                    llm_prompt=row[8],
                    llm_response=row[9],
                    metadata=row[10],
                    was_correct=row[11],
                )
                for row in rows
            ]

    async def save_conversation(
        self,
        agent_id: str,
        from_agent: Optional[str],
        from_human: Optional[str],
        message: str,
        response: str,
        context: dict,
        related_analysis_ids: list[int],
    ) -> int:
        """Store a conversation.

        Args:
            agent_id: Agent being questioned
            from_agent: Questioner agent ID (if agent)
            from_human: Questioner username (if human)
            message: The question
            response: Agent's response
            context: Additional context
            related_analysis_ids: Related analyses

        Returns:
            ID of stored conversation
        """
        async with self.pool.connection() as conn:
            result = await conn.execute(
                """
                INSERT INTO agent_conversations
                (agent_id, from_agent, from_human, message, response, context,
                 related_analysis_ids)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    agent_id,
                    from_agent,
                    from_human,
                    message,
                    response,
                    json.dumps(context),
                    related_analysis_ids,
                ),
            )
            row = await result.fetchone()
            return row[0]

    async def mark_incorrect(self, analysis_id: int) -> None:
        """Mark an analysis as incorrect.

        Args:
            analysis_id: Analysis to mark
        """
        async with self.pool.connection() as conn:
            await conn.execute(
                """
                UPDATE agent_analyses
                SET was_correct = FALSE,
                    correction_timestamp = NOW()
                WHERE id = %s
                """,
                (analysis_id,),
            )

    async def save_correction(
        self, agent_id: str, original_analysis_id: int, correction: Correction
    ) -> int:
        """Store a correction.

        Args:
            agent_id: Agent making the correction
            original_analysis_id: Original analysis being corrected
            correction: Correction details

        Returns:
            ID of stored correction
        """
        async with self.pool.connection() as conn:
            # First mark original as incorrect
            await self.mark_incorrect(original_analysis_id)

            # Store correction
            result = await conn.execute(
                """
                INSERT INTO agent_corrections
                (agent_id, original_analysis_id, timestamp, trigger,
                 new_findings, reasoning, learned_lessons)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    agent_id,
                    original_analysis_id,
                    correction.timestamp,
                    correction.trigger,
                    json.dumps([f.to_dict() for f in correction.new_findings]),
                    correction.reasoning,
                    json.dumps(correction.learned_lessons),
                ),
            )
            row = await result.fetchone()
            correction_id = row[0]

            # Link back to original
            await conn.execute(
                """
                UPDATE agent_analyses
                SET correction_id = %s
                WHERE id = %s
                """,
                (correction_id, original_analysis_id),
            )

            return correction_id
