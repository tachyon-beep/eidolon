"""Data models for agent analysis and communication."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Finding:
    """A bug or issue found during analysis."""

    location: str  # "file:line" or "file:line:column"
    severity: str  # "critical" | "high" | "medium" | "low" | "info"
    type: str  # "bug" | "security" | "performance" | "architecture" | "style"
    description: str
    suggested_fix: Optional[str] = None
    code_snippet: Optional[str] = None
    agent_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "location": self.location,
            "severity": self.severity,
            "type": self.type,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "code_snippet": self.code_snippet,
            "agent_id": self.agent_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Analysis:
    """A complete analysis performed by an agent."""

    timestamp: datetime
    commit_sha: str
    trigger: str  # "initial_audit" | "code_change" | "cross_agent_question" | "manual"
    findings: list[Finding]
    reasoning: str  # Agent's explanation of its analysis
    confidence: float = 0.0  # 0.0 to 1.0
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "commit_sha": self.commit_sha,
            "trigger": self.trigger,
            "findings": [f.to_dict() for f in self.findings],
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "llm_prompt": self.llm_prompt,
            "llm_response": self.llm_response,
            "metadata": self.metadata,
        }


@dataclass
class Question:
    """A question posed to an agent."""

    text: str
    from_agent: Optional[str] = None  # Agent ID or "human:username"
    from_human: Optional[str] = None  # Username if human
    context: dict[str, Any] = field(default_factory=dict)
    about_commit: Optional[str] = None


@dataclass
class Answer:
    """An agent's answer to a question."""

    text: str
    confidence: float = 1.0
    supporting_analyses: list[int] = field(default_factory=list)  # Analysis IDs
    reasoning: Optional[str] = None


@dataclass
class Correction:
    """A correction to a previous analysis."""

    original_analysis_id: int
    trigger: str  # What caused the correction
    new_findings: list[Finding]
    reasoning: str  # Why the original was wrong
    learned_lessons: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Report:
    """A report of findings from an agent."""

    agent_id: str
    scope: "Scope"  # Forward reference
    findings: list[Finding]
    summary: str
    children: list["Report"] = field(default_factory=list)  # For hierarchical reports
    metadata: dict[str, Any] = field(default_factory=dict)

    def total_findings(self) -> int:
        """Count total findings including children."""
        total = len(self.findings)
        for child in self.children:
            total += child.total_findings()
        return total

    def findings_by_severity(self) -> dict[str, int]:
        """Count findings by severity."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for finding in self.findings:
            counts[finding.severity] = counts.get(finding.severity, 0) + 1
        for child in self.children:
            child_counts = child.findings_by_severity()
            for severity, count in child_counts.items():
                counts[severity] += count
        return counts
