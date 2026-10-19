from __future__ import annotations

import json

from .models import ExperienceRecord, WikiNote


CONSOLIDATOR_SYSTEM_PROMPT = """You maintain a durable strategy wiki from evaluated agent experience.

Your job is curation, not summarization. Raw evidence is stored elsewhere. Add or change a wiki
note only when the evidence supports reusable, actionable knowledge.

Rules:
1. Ground every decision in the supplied experience IDs. Never invent evidence or outcomes.
2. Prefer no-op when an observation is obvious, one-off, redundant, unsupported, or merely a task answer.
3. A strategy must state a trigger, concise procedure, applicability boundary, and verification method.
4. An antipattern must state the tempting action, observed failure, safer alternative, and verification.
5. Environment notes contain stable facts or constraints, never imperative procedures.
6. Merge with an existing note when the core claim is the same. Revise only when evidence changes
   its scope or procedure. Record contradictory evidence instead of silently overwriting it.
7. Do not paste complete programs, transcripts, benchmark answers, secrets, or long code fragments.
   Preserve only the minimum pseudocode or command shape needed to express the reusable idea.
8. Keep notes model- and task-agnostic unless the evidence demonstrates a genuine boundary.
9. Never modify pinned notes. Never archive a note solely because it is old.
10. Return strict JSON matching the requested schema, with no prose outside JSON.
"""


COMPACTION_SYSTEM_PROMPT = """You compact a strategy wiki without losing supported knowledge.

Merge only genuinely overlapping notes. Preserve triggers, boundaries, verification rules,
contradictions, evidence IDs, and user-pinned material. Remove repetition and incidental code,
not distinct advice. If compaction would weaken traceability or change meaning, return no-op.
Return strict JSON only.
"""


def build_consolidation_prompt(
    experiences: list[ExperienceRecord],
    related_notes: list[WikiNote],
) -> str:
    schema = {
        "decisions": [{
            "action": "no-op|create|merge|revise|contradict|archive",
            "rationale": "evidence-grounded reason",
            "evidence_ids": ["experience-id"],
            "target_id": "required for merge/revise/contradict/archive, otherwise null",
            "note": {
                "note_id": "lowercase-hyphenated-id",
                "kind": "strategy|antipattern|environment",
                "title": "short title",
                "claim": "one reusable claim",
                "trigger": "when this applies",
                "guidance": ["concise actionable steps"],
                "verification": ["observable checks"],
                "applicability": ["domains or conditions"],
                "limitations": ["known exclusions"],
                "relation": "motivates|supports|contradicts",
            },
        }]
    }
    return (
        CONSOLIDATOR_SYSTEM_PROMPT
        + "\nOUTPUT SCHEMA:\n"
        + json.dumps(schema, indent=2)
        + "\n\nEXISTING RELATED NOTES:\n"
        + json.dumps([note.model_dump(mode="json") for note in related_notes], indent=2)
        + "\n\nNEW EXPERIENCES:\n"
        + json.dumps([record.model_dump(mode="json") for record in experiences], indent=2)
    )


def build_compaction_prompt(notes: list[WikiNote]) -> str:
    return (
        COMPACTION_SYSTEM_PROMPT
        + "\n\nReturn {\"decisions\": [...]} using the consolidation decision schema.\n\nNOTES:\n"
        + json.dumps([note.model_dump(mode="json") for note in notes], indent=2)
    )
