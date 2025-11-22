from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AgentScope(str, Enum):
    SYSTEM = "System"
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"


class AgentStatus(str, Enum):
    IDLE = "Idle"
    ANALYZING = "Analyzing"
    REPORTING = "Reporting"
    COMPLETED = "Completed"
    ERROR = "Error"


class AgentMessage(BaseModel):
    """Represents a single message in the agent's session"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    role: str = Field(..., description="user/assistant/system")
    content: str = Field(..., description="Message content")
    tokens_in: int = Field(default=0)
    tokens_out: int = Field(default=0)
    tool_calls: List[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0)


class AgentSnapshot(BaseModel):
    """Snapshot of code or data the agent is analyzing"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str = Field(..., description="file_diff/ast_extract/test_run")
    data: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    id: str = Field(..., description="Unique agent ID (AGN-SCOPE-SEQ)")
    scope: AgentScope
    target: str = Field(..., description="What this agent is analyzing (file path, function name, etc)")
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)

    # Session tracking
    session_id: Optional[str] = None
    messages: List[AgentMessage] = Field(default_factory=list)
    snapshots: List[AgentSnapshot] = Field(default_factory=list)

    # Analysis results
    findings: List[str] = Field(default_factory=list, description="Key findings from analysis")
    cards_created: List[str] = Field(default_factory=list, description="Card IDs created by this agent")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Costs
    total_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0)

    class Config:
        use_enum_values = True

    def add_message(self, role: str, content: str, tokens_in: int = 0,
                   tokens_out: int = 0, tool_calls: List[str] = None,
                   latency_ms: float = 0.0):
        """Add a message to the agent's session"""
        msg = AgentMessage(
            role=role,
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tool_calls=tool_calls or [],
            latency_ms=latency_ms
        )
        self.messages.append(msg)
        self.total_tokens += tokens_in + tokens_out

    def add_snapshot(self, snapshot_type: str, data: Dict[str, Any]):
        """Add a snapshot of analyzed data"""
        snapshot = AgentSnapshot(type=snapshot_type, data=data)
        self.snapshots.append(snapshot)

    def update_status(self, new_status: AgentStatus):
        """Update agent status with timestamp tracking"""
        self.status = new_status
        if new_status == AgentStatus.ANALYZING and not self.started_at:
            self.started_at = datetime.utcnow()
        elif new_status == AgentStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
