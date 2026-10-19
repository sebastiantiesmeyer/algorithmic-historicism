from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

import yaml

from ..evaluation.base import EvaluationResult
from ..llm.base import LLMProvider
from ..skills.format import SkillDocument, load_skill_document
from ..wiki.consolidator import PromptedConsolidator
from ..wiki.workspace import WikiWorkspace
from .engine import EvolutionEngine
from .memory import TraceMemoryMaintainer
from .models import BenchmarkCase, BenchmarkSuite, RolloutTrace, SkillProposal


SPLIT_SEED = "bird-mini-dev-v1"


def database_path(root: Path, db_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", db_id):
        raise ValueError(f"Invalid BIRD database ID: {db_id}")
    candidates = [root / db_id / f"{db_id}.sqlite", root / f"{db_id}.sqlite"]
    candidates.extend(sorted((root / db_id).glob("*.sqlite")))
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(f"SQLite database for {db_id} not found below {root}")


def load_bird_mini_dev(
    data_path: Path,
    databases_root: Path,
    *,
    limit_per_split: int | None = None,
    database_id: str | None = None,
    seed: str = SPLIT_SEED,
) -> tuple[BenchmarkSuite, dict[str, str]]:
    """Load the official SQLite rows while keeping oracle evidence out of public cases."""
    raw = data_path.read_text(encoding="utf-8")
    rows = json.loads(raw) if data_path.suffix == ".json" else [
        json.loads(line) for line in raw.splitlines() if line.strip()
    ]
    if not isinstance(rows, list) or not rows:
        raise ValueError("BIRD Mini-Dev data must be a nonempty JSON array or JSONL file")
    groups: dict[str, list[dict]] = defaultdict(list)
    seen: set[str] = set()
    for row in rows:
        case_id = str(row["question_id"])
        db_id = str(row["db_id"])
        if database_id is not None and db_id != database_id:
            continue
        if case_id in seen:
            raise ValueError(f"Duplicate BIRD question ID: {case_id}")
        if not str(row["question"]).strip() or not str(row["SQL"]).strip():
            raise ValueError(f"Empty BIRD question or gold SQL: {case_id}")
        seen.add(case_id)
        database_path(databases_root, db_id)
        groups[db_id].append(row)
    if not groups:
        raise ValueError(f"No BIRD questions found for database {database_id!r}")

    cases: list[BenchmarkCase] = []
    evidence: dict[str, str] = {}
    for db_id, group in sorted(groups.items()):
        if len(group) < 3:
            raise ValueError(f"At least three questions are required for database {db_id}")
        group.sort(key=lambda row: hashlib.sha256(
            f"{seed}:{row['question_id']}".encode("utf-8")
        ).hexdigest())
        train_end = max(1, round(len(group) * 0.6))
        validation_end = min(len(group) - 1, max(train_end + 1, round(len(group) * 0.8)))
        for split, selected in (
            ("training", group[:train_end]),
            ("validation", group[train_end:validation_end]),
            ("test", group[validation_end:]),
        ):
            if limit_per_split is not None:
                selected = selected[:limit_per_split]
            for row in selected:
                case_id = str(row["question_id"])
                cases.append(BenchmarkCase(
                    case_id=case_id,
                    input=str(row["question"]),
                    expected=str(row["SQL"]),
                    split=split,
                    metadata={"db_id": db_id, "difficulty": str(row.get("difficulty", ""))},
                ))
                evidence[case_id] = str(row.get("evidence") or "")
    suite = BenchmarkSuite(name="bird-mini-dev-sqlite", cases=cases)
    suite.validate_splits()
    return suite, evidence


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_bird_mini_dev_lock(
    data_path: Path,
    databases_root: Path,
    *,
    limit_per_split: int | None = 10,
    database_id: str | None = None,
) -> dict[str, object]:
    """Record the exact public inputs and selected cases without embedding answers."""
    suite, _ = load_bird_mini_dev(
        data_path, databases_root, limit_per_split=limit_per_split, database_id=database_id
    )
    return _protocol_lock(suite, data_path, databases_root, limit_per_split, database_id)


def _protocol_lock(
    suite: BenchmarkSuite,
    data_path: Path,
    databases_root: Path,
    limit_per_split: int | None,
    database_id: str | None,
) -> dict[str, object]:
    database_files = []
    for db_id in sorted({str(case.metadata["db_id"]) for case in suite.cases}):
        db_path = database_path(databases_root, db_id)
        paths = [db_path, *sorted((db_path.parent / "database_description").glob("*.csv"))]
        database_files.extend({
            "path": path.relative_to(databases_root).as_posix(),
            "sha256": _sha256_file(path),
        } for path in paths)
    return {
        "format_version": 1,
        "benchmark": suite.name,
        "split_seed": SPLIT_SEED,
        "split_method": "sha256(seed:question_id), per database, 60/20/20",
        "dataset_sha256": _sha256_file(data_path),
        "database_id": database_id,
        "limit_per_split": limit_per_split,
        "database_files": database_files,
        "cases": {
            split: [
                {"case_id": case.case_id, "db_id": case.metadata["db_id"]}
                for case in suite.select(split)
            ]
            for split in ("training", "validation", "test")
        },
    }


class BirdMiniDevAgent:
    def __init__(self, databases_root: Path, provider: LLMProvider):
        self.databases_root = databases_root
        self.provider = provider
        self._schemas: dict[str, str] = {}

    def _schema(self, db_id: str) -> str:
        if db_id not in self._schemas:
            path = database_path(self.databases_root, db_id)
            with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as connection:
                tables = connection.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'view') "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            schema = "\n".join(sql or name for name, sql in tables)
            description_dir = path.parent / "database_description"
            descriptions = []
            for description in sorted(description_dir.glob("*.csv")):
                descriptions.append(f"{description.name}:\n{description.read_text(encoding='utf-8-sig')}")
            if descriptions:
                detail = "\n\nCOLUMN DESCRIPTIONS:\n" + "\n".join(descriptions)
                available = max(0, 30_000 - len(schema))
                schema += detail[:available]
                if len(detail) > available:
                    schema += "\n[Column descriptions truncated]"
            self._schemas[db_id] = schema
        return self._schemas[db_id]

    def run(self, case: BenchmarkCase, skill: SkillDocument | None) -> RolloutTrace:
        db_id = str(case.metadata["db_id"])
        prompt = (
            "Write one SQLite SELECT query answering the question. Return only SQL. "
            "Use the schema and any relevant learned knowledge below.\n\n"
            f"DATABASE: {db_id}\nSCHEMA:\n{self._schema(db_id)}\n\n"
            f"LEARNED KNOWLEDGE:\n{skill.instructions if skill else 'None'}\n\n"
            f"QUESTION:\n{case.input}"
        )
        response = self.provider.complete(prompt).strip()
        match = re.fullmatch(r"```(?:sql|sqlite)?\s*(.*?)\s*```", response, re.I | re.S)
        prediction = match.group(1).strip() if match else response
        return RolloutTrace(
            case_id=case.case_id,
            split=case.split,
            input=case.input,
            expected="",
            prediction=prediction,
            skill_name=skill.name if skill else None,
            events=[{"operation": "generate-sql", "db_id": db_id,
                     "prompt": prompt, "response": response}],
        )


def _execute_read_only(db_path: Path, sql: str, timeout_seconds: float) -> list[tuple]:
    deadline = time.monotonic() + timeout_seconds
    allowed = {sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION}
    if hasattr(sqlite3, "SQLITE_RECURSIVE"):
        allowed.add(sqlite3.SQLITE_RECURSIVE)
    with sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise ValueError("SQL did not return a result set")
        return cursor.fetchall()


def _raw_trace_skill(wiki: WikiWorkspace, run_name: str, case: BenchmarkCase) -> SkillDocument | None:
    run_id = re.sub(r"[^a-z0-9]+", "-", run_name.lower()).strip("-") or "run"
    raw_root = wiki.evidence_dir / "raw" / run_id
    query_tokens = set(re.findall(r"[a-z0-9]+", case.input.lower()))
    ranked: list[tuple[int, str]] = []
    for path in raw_root.rglob("*.json"):
        trace = json.loads(path.read_text(encoding="utf-8"))
        events = trace.get("events") or []
        if not events or events[0].get("db_id") != case.metadata["db_id"]:
            continue
        overlap = len(query_tokens & set(re.findall(r"[a-z0-9]+", trace["input"].lower())))
        observations = trace.get("evaluation", {}).get("generalizable_observations", [])
        summary = (
            f"Question: {trace['input']}\nAttempted SQL: {trace['prediction']}\n"
            f"Score: {trace['score']}\nFeedback: {trace['evaluation']['critique']}\n"
            f"Observation: {'; '.join(observations)}"
        )
        ranked.append((overlap, summary))
    if not ranked:
        return None
    ranked.sort(key=lambda item: -item[0])
    return SkillDocument(
        name="raw-training-traces",
        description="Uncurated prior attempts from the same database.",
        instructions="# Raw training traces\n\n" + "\n\n".join(item[1] for item in ranked[:3]),
    )


class BirdMiniDevEvaluator:
    """Per-case BIRD execution accuracy: compare sets of returned rows."""

    def __init__(self, databases_root: Path, evidence: dict[str, str], timeout_seconds: float = 5.0):
        self.databases_root = databases_root
        self.evidence = evidence
        self.timeout_seconds = timeout_seconds

    def evaluate(self, case: BenchmarkCase, trace: RolloutTrace) -> EvaluationResult:
        db_id = str(case.metadata["db_id"])
        path = database_path(self.databases_root, db_id)
        try:
            gold_rows = _execute_read_only(path, case.expected, self.timeout_seconds)
        except (sqlite3.Error, ValueError) as exc:
            raise ValueError(f"BIRD gold SQL failed for {case.case_id}: {exc}") from exc
        try:
            predicted_rows = _execute_read_only(path, trace.prediction, self.timeout_seconds)
            score = float(set(predicted_rows) == set(gold_rows))
            critique = "execution result matched" if score else "execution result differed"
        except (sqlite3.Error, ValueError) as exc:
            score = 0.0
            critique = f"SQL execution failed: {exc}"
        observation = self.evidence.get(case.case_id, "") if case.split == "training" else ""
        return EvaluationResult(
            score=score,
            passed=bool(score),
            critique=critique,
            scores={"execution_accuracy": score},
            generalizable_observations=[observation] if observation else [],
            details={"db_id": db_id, "difficulty": case.metadata.get("difficulty", "")},
        )


class BirdWikiSkillProposer:
    def propose(
        self, wiki: WikiWorkspace, incumbent: SkillDocument | None, iteration: int
    ) -> SkillProposal | None:
        notes = [note for note in wiki.list_notes() if note.status in {"candidate", "accepted"}]
        if not notes:
            return None
        notes.sort(key=lambda note: note.note_id)
        instructions = "# Learned database knowledge\n\n" + "\n\n".join(
            f"## {note.title}\nWhen: {note.trigger}\n"
            + "\n".join(f"- {step}" for step in note.guidance)
            + "\nCheck: " + "; ".join(note.verification)
            + "\nApplicability: " + "; ".join(note.applicability)
            + "\nLimitations: " + "; ".join(note.limitations)
            for note in notes
        )
        instructions = instructions.strip()
        if incumbent and incumbent.instructions.strip() == instructions:
            return None
        return SkillProposal(
            name=f"bird-mini-dev-v{iteration}",
            description="Reusable database conventions and SQL verification guidance.",
            instructions=instructions,
            rationale=f"Consolidated {len(notes)} evidence-backed wiki notes from training attempts.",
            source_patterns=[note.note_id for note in notes],
        )


def _load_incumbent(wiki: WikiWorkspace) -> SkillDocument | None:
    active = wiki.active_skill("bird-mini-dev-sqlite")
    if active is not None:
        return load_skill_document(wiki.skills_dir / active / "SKILL.md")
    # Migrate older wikis using promotion timestamps, never filename ordering.
    accepted = list(wiki.skills_dir.glob("bird-mini-dev-*/SKILL.md"))
    if not accepted:
        return None
    if len(accepted) > 1:
        dated = []
        for path in accepted:
            metadata_path = path.parent / "metadata.yaml"
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
            timestamp = (metadata or {}).get("decision_date")
            if not timestamp:
                raise ValueError("Legacy wiki has multiple skills without promotion dates; set active-skills.json explicitly")
            dated.append((str(timestamp), path))
        dated.sort(key=lambda item: item[0])
        if dated[-1][0] == dated[-2][0]:
            raise ValueError("Legacy wiki has ambiguous promotion dates; set active-skills.json explicitly")
        selected = dated[-1][1]
    else:
        selected = accepted[0]
    incumbent = load_skill_document(selected)
    wiki.set_active_skill("bird-mini-dev-sqlite", incumbent.name, source="legacy-migration")
    return incumbent


def run_bird_mini_dev(
    workspace: Path,
    wiki_root: Path,
    data_path: Path,
    databases_root: Path,
    agent_provider: LLMProvider,
    consolidation_provider: LLMProvider,
    *,
    limit_per_split: int | None = 10,
    database_id: str | None = None,
    max_iterations: int = 1,
    protocol_lock: Path | None = None,
    run_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    suite, evidence = load_bird_mini_dev(
        data_path, databases_root, limit_per_split=limit_per_split, database_id=database_id
    )
    lock = _protocol_lock(suite, data_path, databases_root, limit_per_split, database_id)
    if protocol_lock is not None and json.loads(protocol_lock.read_text(encoding="utf-8")) != lock:
        raise ValueError("Protocol lock differs from the selected cases or input files")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    if any((workspace / name).exists() for name in ("run-config.json", "report.json", "attempts.jsonl", "candidates")):
        raise ValueError("Run workspace already contains a run; choose a fresh workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "protocol-lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    wiki = WikiWorkspace.open(wiki_root, create=True)
    incumbent = _load_incumbent(wiki)
    run_id = re.sub(r"[^a-z0-9]+", "-", workspace.name.lower()).strip("-") or "run"
    if (wiki.evidence_dir / "raw" / run_id).exists():
        raise ValueError("Wiki already contains this run ID; choose a workspace with a new name")
    config = {
        **(run_metadata or {}),
        "benchmark": suite.name,
        "dataset_sha256": lock["dataset_sha256"],
        "split_seed": SPLIT_SEED,
        "database_id": database_id,
        "limit_per_split": limit_per_split,
        "max_iterations": max_iterations,
        "initial_skill": incumbent.name if incumbent else None,
    }
    (workspace / "run-config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    status_path = workspace / "run-status.json"
    status_path.write_text(json.dumps({"status": "running"}), encoding="utf-8")
    engine = EvolutionEngine(
        workspace=workspace,
        wiki_root=wiki_root,
        runner=BirdMiniDevAgent(databases_root, agent_provider),
        evaluator=BirdMiniDevEvaluator(databases_root, evidence),
        maintainer=TraceMemoryMaintainer(workspace.name, PromptedConsolidator(consolidation_provider)),
        proposer=BirdWikiSkillProposer(),
    )
    try:
        report = engine.run(suite, max_iterations=max_iterations, initial_skill=incumbent).model_dump(mode="json")
        raw_scores = []
        for case in suite.select("test"):
            raw_skill = _raw_trace_skill(wiki, workspace.name, case)
            trace = engine._rollout([case], raw_skill, iteration=0, persist=False, condition="raw-trace")[0]
            raw_scores.append(trace.score)
    except BaseException as exc:
        status_path.write_text(json.dumps({"status": "failed", "error_type": type(exc).__name__}), encoding="utf-8")
        raise
    report["raw_trace_test_score"] = sum(raw_scores) / len(raw_scores)
    report["case_counts"] = {split: len(suite.select(split)) for split in ("training", "validation", "test")}
    report["protocol"] = "Custom continual-learning split of BIRD Mini-Dev; not an official leaderboard score"
    (workspace / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    status_path.write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    return report
