from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CardType(str, Enum):
    REQUIREMENT = "Requirement"
    ARCHITECTURE = "Architecture"
    CHANGE = "Change"
    DEFECT = "Defect"
    TEST = "Test"
    REVIEW = "Review"
    AGENT = "Agent"


class CardStatus(str, Enum):
    NEW = "New"
    QUEUED = "Queued"
    IN_ANALYSIS = "In-Analysis"
    PROPOSED = "Proposed"
    IN_REVIEW = "In-Review"
    APPROVED = "Approved"
    BLOCKED = "Blocked"
    DONE = "Done"


class CardPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class CardLink(BaseModel):
    code: List[str] = Field(default_factory=list, description="Code references (repo@rev:path)")
    tests: List[str] = Field(default_factory=list, description="Test references (suite::case)")
    docs: List[str] = Field(default_factory=list, description="Documentation references")


class CardMetrics(BaseModel):
    risk: float = Field(default=0.0, ge=0.0, le=1.0, description="Risk score 0-1")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score 0-1")
    coverage_impact: float = Field(default=0.0, description="Test coverage impact")


class CardLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = Field(..., description="user/agent ID")
    event: str = Field(..., description="Event description")
    diff: Dict[str, Any] = Field(default_factory=dict, description="State changes")


class Routing(BaseModel):
    from_tab: Optional[str] = None
    to_tab: Optional[str] = None


class ProposedFix(BaseModel):
    """Represents a proposed code fix"""
    original_code: str = Field(..., description="Original code snippet")
    fixed_code: str = Field(..., description="Fixed code snippet")
    explanation: str = Field(..., description="Explanation of the fix")
    file_path: str = Field(..., description="File to be modified")
    line_start: int = Field(..., description="Start line of the fix")
    line_end: int = Field(..., description="End line of the fix")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in fix")
    validated: bool = Field(default=False, description="Whether fix has been AST validated")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors if any")


class Card(BaseModel):
    id: str = Field(..., description="Unique card ID (MONAD-YYYY-TYPE-SEQ)")
    type: CardType
    title: str
    summary: str = Field(default="", description="Markdown summary")
    status: CardStatus = Field(default=CardStatus.NEW)
    priority: CardPriority = Field(default=CardPriority.P2)
    owner_agent: Optional[str] = None
    parent: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    links: CardLink = Field(default_factory=CardLink)
    metrics: CardMetrics = Field(default_factory=CardMetrics)
    log: List[CardLogEntry] = Field(default_factory=list)
    routing: Routing = Field(default_factory=Routing)
    proposed_fix: Optional[ProposedFix] = Field(default=None, description="Proposed code fix")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True

    def add_log_entry(self, actor: str, event: str, diff: Dict[str, Any] = None):
        """Add a log entry to the card"""
        entry = CardLogEntry(
            actor=actor,
            event=event,
            diff=diff or {}
        )
        self.log.append(entry)
        self.updated_at = datetime.utcnow()

    def update_status(self, new_status: CardStatus, actor: str = "system"):
        """Update card status with logging"""
        old_status = self.status
        self.status = new_status
        self.add_log_entry(
            actor=actor,
            event=f"Status changed from {old_status} to {new_status}",
            diff={"status": {"old": old_status, "new": new_status}}
        )
