from pathlib import Path

import pytest

from algorithmic_historicism.wiki.consolidator import EvidenceConsolidator
from algorithmic_historicism.wiki.models import ExperienceRecord, MemoryCandidate
from algorithmic_historicism.wiki.prompts import build_consolidation_prompt
from algorithmic_historicism.wiki.workspace import WikiWorkspace


def candidate(relation: str = "supports") -> MemoryCandidate:
    return MemoryCandidate(
        note_id="minimal-mutation",
        kind="strategy",
        title="Minimal mutation",
        claim="Change only the requested property.",
        trigger="A structured artifact needs one localized edit.",
        guidance=["Locate the narrowest target.", "Preserve unrelated structure."],
        verification=["Compare requested fields and preserved fields independently."],
        applicability=["structured editing"],
        limitations=["Not suitable when regeneration is explicitly requested."],
        relation=relation,
    )


def experience(identifier: str, relation: str = "supports") -> ExperienceRecord:
    return ExperienceRecord(
        experience_id=identifier,
        source="test-run",
        task_summary="Change one property without changing the rest.",
        outcome="success" if relation == "supports" else "failure",
        score=1.0 if relation == "supports" else 0.0,
        memory_candidates=[candidate(relation)],
    )


def test_workspace_initializes_versioned_layout(tmp_path: Path):
    wiki = WikiWorkspace.open(tmp_path / "memory", create=True)

    assert (wiki.root / "wiki.yaml").exists()
    assert (wiki.root / "strategies").is_dir()
    assert (wiki.root / "antipatterns").is_dir()
    assert (wiki.root / "environment").is_dir()
    assert (wiki.root / "evidence" / "experiences.jsonl").exists()
    assert (wiki.root / "evidence" / "consolidated.jsonl").exists()
    assert (wiki.root / "revisions").is_dir()
    assert (wiki.root / "archive").is_dir()
    assert (wiki.root / "skills").is_dir()


def test_consolidation_is_idempotent_and_promotes_repeated_support(tmp_path: Path):
    wiki = WikiWorkspace.open(tmp_path / "memory")
    consolidator = EvidenceConsolidator()

    consolidator.consolidate([experience("run-1")], wiki)
    consolidator.consolidate([experience("run-1")], wiki)
    note = wiki.find_note("minimal-mutation")
    assert note is not None
    assert len(note.evidence) == 1
    assert note.status == "candidate"

    consolidator.consolidate([experience("run-2")], wiki)
    note = wiki.find_note("minimal-mutation")
    assert note is not None
    assert len(note.evidence) == 2
    assert note.status == "accepted"
    assert (wiki.root / "revisions" / "minimal-mutation" / "0001.json").exists()


def test_contradiction_disputes_note_and_pinned_note_rejects_automation(tmp_path: Path):
    wiki = WikiWorkspace.open(tmp_path / "memory")
    consolidator = EvidenceConsolidator()
    consolidator.consolidate([experience("run-1"), experience("run-2")], wiki)
    consolidator.consolidate([experience("run-3", "contradicts")], wiki)
    note = wiki.find_note("minimal-mutation")
    assert note is not None
    assert note.status == "disputed"

    note.pinned = True
    wiki.upsert_note(note, actor="human")
    with pytest.raises(PermissionError):
        consolidator.consolidate([experience("run-4")], wiki)

    note.pinned = False
    wiki.upsert_note(note, actor="human")
    consolidator.consolidate([experience("run-4")], wiki)
    assert "run-4" in wiki.consolidated_experience_ids()


def test_prompt_requires_evidence_and_allows_no_op(tmp_path: Path):
    wiki = WikiWorkspace.open(tmp_path / "memory")
    record = experience("run-1")
    prompt = build_consolidation_prompt([record], wiki.list_notes())

    assert "Prefer no-op" in prompt
    assert "Never invent evidence" in prompt
    assert "run-1" in prompt
    assert "Do not paste complete programs" in prompt
