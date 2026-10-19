from __future__ import annotations

import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from ..llm.base import LLMProvider
from .models import (
    ConsolidationDecision,
    EvidenceLink,
    ExperienceRecord,
    MemoryCandidate,
    WikiNote,
)
from .prompts import build_consolidation_prompt
from .workspace import WikiWorkspace


class ConsolidationResponse(BaseModel):
    decisions: list[ConsolidationDecision] = Field(default_factory=list)


class EvidenceConsolidator:
    """Deterministically stores evaluator-supplied candidates with evidence."""

    def consolidate(self, experiences: list[ExperienceRecord], wiki: WikiWorkspace) -> list[str]:
        changed: list[str] = []
        processed = 0
        consolidated_ids = wiki.consolidated_experience_ids()
        for experience in experiences:
            wiki.record_experience(experience)
            if experience.experience_id in consolidated_ids:
                continue
            for candidate in experience.memory_candidates:
                note = self._merge_candidate(wiki, candidate, experience.experience_id)
                wiki.upsert_note(note)
                changed.append(note.note_id)
            wiki.mark_consolidated(experience.experience_id)
            processed += 1
        if processed:
            wiki.append_log(
                f"{datetime.now(timezone.utc).isoformat()}: consolidated {processed} "
                f"experiences; changed={sorted(set(changed)) or ['none']}."
            )
        return sorted(set(changed))

    @staticmethod
    def _merge_candidate(
        wiki: WikiWorkspace,
        candidate: MemoryCandidate,
        experience_id: str,
    ) -> WikiNote:
        existing = wiki.find_note(candidate.note_id)
        link = EvidenceLink(
            experience_id=experience_id,
            relation=candidate.relation,
            detail=candidate.claim,
        )
        if existing is None:
            return WikiNote(
                note_id=candidate.note_id,
                kind=candidate.kind,
                title=candidate.title,
                claim=candidate.claim,
                trigger=candidate.trigger,
                guidance=candidate.guidance,
                verification=candidate.verification,
                applicability=candidate.applicability,
                limitations=candidate.limitations,
                evidence=[link],
            )
        evidence_by_key = {(item.experience_id, item.relation): item for item in existing.evidence}
        evidence_by_key[(link.experience_id, link.relation)] = link
        existing.evidence = list(evidence_by_key.values())
        if candidate.relation == "contradicts":
            existing.status = "disputed"
        return existing


class PromptedConsolidator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def consolidate(self, experiences: list[ExperienceRecord], wiki: WikiWorkspace) -> list[str]:
        consolidated_ids = wiki.consolidated_experience_ids()
        pending = []
        for record in experiences:
            wiki.record_experience(record)
            if record.experience_id not in consolidated_ids:
                pending.append(record)
        if not pending:
            return []
        query = " ".join(record.task_summary for record in pending)
        related = wiki.search(query, limit=8)
        response = self.provider.complete(build_consolidation_prompt(pending, related))
        payload = self._extract_json(response)
        decisions = ConsolidationResponse.model_validate(payload).decisions
        changed: list[str] = []
        for decision in decisions:
            note_id = self._apply(decision, pending, wiki)
            if note_id:
                changed.append(note_id)
        for record in pending:
            wiki.mark_consolidated(record.experience_id)
        return changed

    @staticmethod
    def _extract_json(response: str) -> dict[str, object]:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("Consolidator response must be a JSON object")
        return value

    @staticmethod
    def _apply(
        decision: ConsolidationDecision,
        experiences: list[ExperienceRecord],
        wiki: WikiWorkspace,
    ) -> str | None:
        if decision.action == "no-op":
            return None
        if decision.action == "archive":
            existing = wiki.find_note(str(decision.target_id))
            if existing is None or existing.pinned:
                return None
            existing.status = "archived"
            wiki.upsert_note(existing)
            return existing.note_id
        candidate = decision.note
        target_id = decision.target_id or (candidate.note_id if candidate else None)
        existing = wiki.find_note(str(target_id)) if target_id else None
        if decision.action == "create":
            existing = None
        if candidate is None and existing is None:
            return None
        source = candidate or MemoryCandidate(
            note_id=existing.note_id,
            kind=existing.kind,
            title=existing.title,
            claim=existing.claim,
            trigger=existing.trigger,
            guidance=existing.guidance,
            verification=existing.verification,
            applicability=existing.applicability,
            limitations=existing.limitations,
            relation="contradicts" if decision.action == "contradict" else "motivates",
        )
        links = list(existing.evidence) if existing else []
        known_ids = {record.experience_id for record in experiences}
        for evidence_id in decision.evidence_ids:
            if evidence_id not in known_ids:
                raise ValueError(f"Consolidation cited unknown experience: {evidence_id}")
            relation = "contradicts" if decision.action == "contradict" else source.relation
            links.append(EvidenceLink(
                experience_id=evidence_id,
                relation=relation,
                detail=decision.rationale,
            ))
        note = WikiNote(
            note_id=source.note_id if existing is None else existing.note_id,
            kind=source.kind,
            title=source.title,
            claim=source.claim,
            trigger=source.trigger,
            guidance=source.guidance,
            verification=source.verification,
            applicability=source.applicability,
            limitations=source.limitations,
            evidence=links,
            status="disputed" if decision.action == "contradict" else (existing.status if existing else "candidate"),
            pinned=existing.pinned if existing else False,
        )
        wiki.upsert_note(note)
        return note.note_id
