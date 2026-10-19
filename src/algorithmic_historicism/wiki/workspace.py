from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .models import EvidenceLink, ExperienceRecord, WikiNote


SCHEMA_VERSION = 1
_SAFE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_KIND_DIR = {
    "strategy": "strategies",
    "antipattern": "antipatterns",
    "environment": "environment",
}


class WikiWorkspace:
    def __init__(self, root: Path):
        self.root = root
        self.evidence_dir = root / "evidence"
        self.revisions_dir = root / "revisions"
        self.skills_dir = root / "skills"
        self.candidates_dir = root / "candidates"

    @classmethod
    def open(cls, root: Path, *, create: bool = True, name: str | None = None) -> "WikiWorkspace":
        root = root.resolve()
        manifest = root / "wiki.yaml"
        if not manifest.exists():
            if not create:
                raise FileNotFoundError(f"Wiki does not exist: {root}")
            cls._initialize(root, name or root.name)
        payload = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        version = payload.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported wiki schema version {version!r}; expected {SCHEMA_VERSION}")
        workspace = cls(root)
        workspace._ensure_layout()
        return workspace

    @staticmethod
    def _initialize(root: Path, name: str) -> None:
        root.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "policy": {
                "minimum_support_for_acceptance": 2,
                "maximum_note_characters": 12000,
                "automation_may_modify_pinned_notes": False,
            },
        }
        (root / "wiki.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False), encoding="utf-8"
        )
        workspace = WikiWorkspace(root)
        workspace._ensure_layout()
        workspace._refresh_index()

    def _ensure_layout(self) -> None:
        for name in (
            "strategies",
            "antipatterns",
            "environment",
            "evidence",
            "revisions",
            "archive",
            "skills",
            "candidates",
        ):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        for name, heading in (("log.md", "Evolution log"), ("skill-impact.md", "Skill impact")):
            path = self.root / name
            if not path.exists():
                path.write_text(f"# {heading}\n\n", encoding="utf-8")
        experiences = self.evidence_dir / "experiences.jsonl"
        if not experiences.exists():
            experiences.write_text("", encoding="utf-8")
        consolidated = self.evidence_dir / "consolidated.jsonl"
        if not consolidated.exists():
            consolidated.write_text("", encoding="utf-8")

    @staticmethod
    def _validate_id(value: str) -> str:
        if not _SAFE_ID.fullmatch(value):
            raise ValueError(f"Invalid wiki identifier: {value}")
        return value

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

    def record_experience(self, record: ExperienceRecord) -> bool:
        path = self.evidence_dir / "experiences.jsonl"
        existing_ids = {
            json.loads(line)["experience_id"]
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if record.experience_id in existing_ids:
            return False
        with path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        return True

    def experiences(self) -> list[ExperienceRecord]:
        path = self.evidence_dir / "experiences.jsonl"
        return [
            ExperienceRecord.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def consolidated_experience_ids(self) -> set[str]:
        path = self.evidence_dir / "consolidated.jsonl"
        return {
            str(json.loads(line)["experience_id"])
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def mark_consolidated(self, experience_id: str) -> bool:
        if experience_id in self.consolidated_experience_ids():
            return False
        path = self.evidence_dir / "consolidated.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "experience_id": experience_id,
                "consolidated_at": datetime.now(timezone.utc).isoformat(),
            }) + "\n")
        return True

    def _note_path(self, kind: str, note_id: str, suffix: str) -> Path:
        self._validate_id(note_id)
        if kind not in _KIND_DIR:
            raise ValueError(f"Unsupported wiki note kind: {kind}")
        return self.root / _KIND_DIR[kind] / f"{note_id}.{suffix}"

    def find_note(self, note_id: str) -> WikiNote | None:
        self._validate_id(note_id)
        for directory in _KIND_DIR.values():
            path = self.root / directory / f"{note_id}.json"
            if path.exists():
                return WikiNote.model_validate_json(path.read_text(encoding="utf-8"))
        return None

    def list_notes(self, *, include_archived: bool = False) -> list[WikiNote]:
        notes: list[WikiNote] = []
        for directory in _KIND_DIR.values():
            for path in sorted((self.root / directory).glob("*.json")):
                note = WikiNote.model_validate_json(path.read_text(encoding="utf-8"))
                if include_archived or note.status != "archived":
                    notes.append(note)
        return notes

    def upsert_note(self, note: WikiNote, *, actor: str = "automation") -> WikiNote:
        self._validate_id(note.note_id)
        existing = self.find_note(note.note_id)
        if existing and existing.pinned and actor != "human":
            raise PermissionError(f"Pinned wiki note requires human modification: {note.note_id}")
        if existing and existing.kind != note.kind:
            raise ValueError(f"Wiki note kind cannot change: {note.note_id}")
        if existing:
            revision_dir = self.revisions_dir / note.note_id
            revision_dir.mkdir(parents=True, exist_ok=True)
            snapshot = revision_dir / f"{existing.revision:04d}.json"
            if not snapshot.exists():
                self._atomic_write(snapshot, existing.model_dump_json(indent=2))
            note.created_at = existing.created_at
            note.revision = existing.revision + 1
        note.updated_at = datetime.now(timezone.utc)
        note.confidence = self._confidence(note.evidence)
        if (
            note.status == "candidate"
            and len({item.experience_id for item in note.evidence if item.relation == "supports"}) >= 2
            and not any(item.relation == "contradicts" for item in note.evidence)
        ):
            note.status = "accepted"
        json_path = self._note_path(note.kind, note.note_id, "json")
        markdown_path = self._note_path(note.kind, note.note_id, "md")
        self._atomic_write(json_path, note.model_dump_json(indent=2))
        self._atomic_write(markdown_path, self.render_note(note))
        self._refresh_index()
        return note

    @staticmethod
    def _confidence(evidence: list[EvidenceLink]) -> float:
        supports = len({item.experience_id for item in evidence if item.relation == "supports"})
        contradictions = len({item.experience_id for item in evidence if item.relation == "contradicts"})
        motivates = len({item.experience_id for item in evidence if item.relation == "motivates"})
        denominator = supports + contradictions + motivates + 2
        return round((supports + 0.25 * motivates) / denominator, 4)

    @staticmethod
    def render_note(note: WikiNote) -> str:
        def bullets(values: list[str], empty: str = "None recorded.") -> str:
            return "\n".join(f"- {value}" for value in values) if values else empty

        evidence = "\n".join(
            f"- `{item.experience_id}` ({item.relation}): {item.detail}" for item in note.evidence
        )
        return (
            f"# {note.title}\n\n"
            f"- ID: `{note.note_id}`\n"
            f"- Kind: `{note.kind}`\n"
            f"- Status: `{note.status}`\n"
            f"- Confidence: `{note.confidence:.4f}`\n"
            f"- Revision: `{note.revision}`\n\n"
            f"## Claim\n\n{note.claim}\n\n"
            f"## Trigger\n\n{note.trigger}\n\n"
            f"## Guidance\n\n{bullets(note.guidance)}\n\n"
            f"## Verification\n\n{bullets(note.verification)}\n\n"
            f"## Applicability\n\n{bullets(note.applicability)}\n\n"
            f"## Limitations\n\n{bullets(note.limitations)}\n\n"
            f"## Evidence\n\n{evidence}\n"
        )

    def _refresh_index(self) -> None:
        sections: list[str] = ["# Knowledge index", ""]
        for kind, directory in _KIND_DIR.items():
            notes = []
            for path in sorted((self.root / directory).glob("*.json")):
                note = WikiNote.model_validate_json(path.read_text(encoding="utf-8"))
                if note.status != "archived":
                    notes.append(note)
            sections.extend([f"## {directory.title()}", ""])
            sections.extend(
                f"- [{note.title}]({directory}/{note.note_id}.md) "
                f"- `{note.status}`, confidence `{note.confidence:.4f}`"
                for note in notes
            )
            sections.append("")
        self._atomic_write(self.root / "index.md", "\n".join(sections).rstrip() + "\n")

    def search(self, query: str, *, limit: int = 5) -> list[WikiNote]:
        tokens = {token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2}
        ranked: list[tuple[float, WikiNote]] = []
        for note in self.list_notes():
            haystack = " ".join([
                note.title,
                note.claim,
                note.trigger,
                *note.guidance,
                *note.applicability,
                *note.limitations,
            ]).lower()
            overlap = sum(1 for token in tokens if token in haystack)
            if overlap:
                ranked.append((overlap + note.confidence, note))
        ranked.sort(key=lambda item: (-item[0], item[1].note_id))
        return [note for _, note in ranked[:limit]]

    def append_log(self, entry: str) -> None:
        path = self.root / "log.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"- {entry}\n")

    def append_skill_impact(
        self,
        *,
        iteration: int,
        candidate: str,
        baseline_score: float,
        candidate_score: float,
        accepted: bool,
        rationale: str,
        diff: str,
    ) -> None:
        path = self.root / "skill-impact.md"
        outcome = "Accepted" if accepted else "Rejected"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                f"## Iteration {iteration}: {candidate}\n\n"
                f"- Outcome: {outcome}\n"
                f"- Baseline validation score: {baseline_score:.4f}\n"
                f"- Candidate validation score: {candidate_score:.4f}\n"
                f"- Rationale: {rationale}\n\n"
                f"```diff\n{diff.rstrip()}\n```\n\n"
            )

    def add_raw_trace(self, run_id: str, iteration: int, case_id: str, payload: dict) -> Path:
        safe_run = self._validate_id(run_id)
        safe_case = self._validate_id(case_id)
        raw_dir = self.evidence_dir / "raw" / safe_run / f"iteration-{iteration:03d}"
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / f"{safe_case}.json"
        if path.exists():
            raise FileExistsError(f"Raw trace is immutable: {path}")
        self._atomic_write(path, json.dumps(payload, indent=2))
        return path
