"""Pydantic models for CogWatch data structures."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DecisionSource(str, Enum):
    OBSIDIAN = "obsidian"
    GITHUB = "github"
    CLAUDE_SESSION = "claude_session"
    GMAIL = "gmail"


class DecisionStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    STALE = "stale"


class ContradictionType(str, Enum):
    DIRECT = "direct_contradiction"
    FORGOTTEN = "forgotten_resolution"
    STALE_THREAD = "stale_thread"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionRecord(BaseModel):
    id: str | None = None
    source: DecisionSource
    content: str
    context: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    embedding: list[float] | None = None
    tags: list[str] = Field(default_factory=list)
    status: DecisionStatus = DecisionStatus.ACTIVE


class ContradictionResult(BaseModel):
    is_contradiction: bool
    explanation: str
    severity: Severity
    contradiction_type: ContradictionType | None = None


class PersonaResponse(BaseModel):
    persona_name: str
    response: str


class Alert(BaseModel):
    id: str | None = None
    old_decision_id: str
    new_decision_id: str
    contradiction_type: ContradictionType
    severity: Severity
    explanation: str
    persona_responses: list[PersonaResponse] = Field(default_factory=list)
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Persona(BaseModel):
    id: str | None = None
    name: str
    system_prompt: str
    active: bool = True
