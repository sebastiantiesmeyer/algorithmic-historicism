from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


NoteKind = Literal["strategy", "antipattern", "environment"]
NoteStatus = Literal["candidate", "accepted", "disputed", "deprecated", "archived"]
EvidenceRelation = Literal["motivates", "supports", "contradicts"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceLink(BaseModel):
    experience_id: str
    relation: EvidenceRelation
    detail: str = ""


class MemoryCandidate(BaseModel):
    note_id: str
    kind: NoteKind
    title: str
    claim: str
    trigger: str
    guidance: list[str]
    verification: list[str]
    applicability: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    relation: EvidenceRelation = "motivates"


class ExperienceRecord(BaseModel):
    experience_id: str
    source: str
    task_summary: str
    outcome: str
    score: float | None = None
    strategy_ids: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    evaluation: dict[str, object] = Field(default_factory=dict)
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class WikiNote(BaseModel):
    note_id: str
    kind: NoteKind
    title: str
    claim: str
    trigger: str
    guidance: list[str]
    verification: list[str]
    applicability: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)
    status: NoteStatus = "candidate"
    confidence: float = 0.0
    revision: int = 1
    pinned: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def require_reusable_content(self) -> "WikiNote":
        if not self.claim.strip() or not self.trigger.strip():
            raise ValueError("Wiki notes require a claim and applicability trigger")
        if not self.guidance or not self.verification:
            raise ValueError("Wiki notes require guidance and verification")
        if not self.evidence:
            raise ValueError("Wiki notes require at least one evidence link")
        if len(self.model_dump_json()) > 12_000:
            raise ValueError("Wiki note exceeds the 12,000-character curation limit")
        return self


class ConsolidationDecision(BaseModel):
    action: Literal["no-op", "create", "merge", "revise", "contradict", "archive"]
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    target_id: str | None = None
    note: MemoryCandidate | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ConsolidationDecision":
        if self.action == "create" and self.note is None:
            raise ValueError("create decisions require a note")
        if self.action in {"merge", "revise", "contradict", "archive"} and not self.target_id:
            raise ValueError(f"{self.action} decisions require target_id")
        return self
