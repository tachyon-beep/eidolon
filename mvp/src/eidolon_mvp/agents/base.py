"""Base agent class for hierarchical code analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .models import Analysis, Answer, Correction, Finding, Question, Report


@dataclass
class Scope:
    """Defines what code an agent is responsible for."""

    type: str  # "function" | "module" | "class" | "system"
    id: Optional[str] = None  # e.g., "auth.login.validate_token"
    path: Optional[str] = None  # e.g., "src/auth/login.py"
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def __str__(self) -> str:
        if self.id:
            return f"{self.type}:{self.id}"
        elif self.path:
            return f"{self.type}:{self.path}"
        return f"{self.type}:unknown"


class Agent(ABC):
    """Base class for all agents.

    Agents analyze code within their scope, store reasoning in persistent memory,
    and can be questioned about their conclusions.
    """

    def __init__(self, agent_id: str, scope: Scope, memory_store: "MemoryStore"):
        """Initialize agent.

        Args:
            agent_id: Unique identifier (e.g., "function:auth.login.validate_token")
            scope: What code this agent is responsible for
            memory_store: Storage for persistent memory
        """
        self.agent_id = agent_id
        self.scope = scope
        from ..memory.agent_memory import AgentMemory

        self.memory = AgentMemory(agent_id, memory_store)
        self.findings: list[Finding] = []

    @abstractmethod
    async def analyze(self) -> list[Finding]:
        """Run analysis on this agent's scope.

        Returns:
            List of findings (bugs, issues, etc.)
        """
        pass

    def report(self) -> Report:
        """Generate report of findings.

        Returns:
            Report with findings and summary
        """
        return Report(
            agent_id=self.agent_id,
            scope=self.scope,
            findings=self.findings,
            summary=self._build_summary(),
            children=[],
        )

    async def handle_question(self, question: Question) -> Answer:
        """Answer questions about previous analyses.

        Args:
            question: Question to answer

        Returns:
            Answer with supporting evidence
        """
        # Load relevant analyses
        if question.about_commit:
            analyses = await self.memory.get_analyses(commit_sha=question.about_commit)
        else:
            analyses = await self.memory.get_analyses(limit=5)

        if not analyses:
            return Answer(
                text="I haven't analyzed this yet",
                confidence=1.0,
                reasoning="No previous analyses found",
            )

        # Format analyses for context
        context = self._format_analyses_for_question(analyses, question)

        # For now, return a simple answer based on available data
        # In Week 4, we'll add LLM integration here
        return Answer(
            text=f"Based on {len(analyses)} previous analyses: {context}",
            confidence=0.8,
            supporting_analyses=[a.id for a in analyses if hasattr(a, "id")],
            reasoning="Retrieved from stored analyses",
        )

    async def correct_analysis(
        self, original_analysis_id: int, correction: Correction
    ) -> None:
        """Record a correction to previous analysis.

        Args:
            original_analysis_id: ID of the analysis being corrected
            correction: Correction details
        """
        await self.memory.record_correction(original_analysis_id, correction)

    def _build_summary(self) -> str:
        """Build summary of findings."""
        if not self.findings:
            return "No issues found"

        by_severity = {}
        for finding in self.findings:
            by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1

        parts = []
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = by_severity.get(severity, 0)
            if count > 0:
                parts.append(f"{count} {severity}")

        return f"Found {len(self.findings)} issues: " + ", ".join(parts)

    def _format_analyses_for_question(
        self, analyses: list[Analysis], question: Question
    ) -> str:
        """Format analyses to help answer a question."""
        if not analyses:
            return "No analyses available"

        latest = analyses[0]
        return f"{len(latest.findings)} findings with {latest.confidence:.0%} confidence"
