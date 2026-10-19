import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from algorithmic_historicism.cli import app
from algorithmic_historicism.evolution.bird_mini_dev import (
    BirdMiniDevEvaluator,
    load_bird_mini_dev,
    make_bird_mini_dev_lock,
    run_bird_mini_dev,
)
from algorithmic_historicism.evolution.models import RolloutTrace


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    databases = tmp_path / "databases"
    database_dir = databases / "sample"
    database_dir.mkdir(parents=True)
    with sqlite3.connect(database_dir / "sample.sqlite") as connection:
        connection.execute("CREATE TABLE items (name TEXT, active INTEGER)")
        connection.executemany("INSERT INTO items VALUES (?, ?)", [("one", 1), ("two", 0)])
    description_dir = database_dir / "database_description"
    description_dir.mkdir()
    (description_dir / "items.csv").write_text(
        "column_name,column_description\nactive,One means active\n", encoding="utf-8"
    )
    data = tmp_path / "mini_dev_sqlite.json"
    data.write_text(json.dumps([
        {
            "question_id": index,
            "db_id": "sample",
            "question": f"List active item names, phrasing {index}.",
            "SQL": "SELECT name FROM items WHERE active = 1",
            "evidence": "In this database, active items have active = 1.",
            "difficulty": "simple",
        }
        for index in range(1, 6)
    ]), encoding="utf-8")
    return data, databases


def test_loader_splits_by_question_and_keeps_oracle_evidence_private(tmp_path: Path):
    data, databases = _fixture(tmp_path)
    suite, evidence = load_bird_mini_dev(data, databases)

    assert {case.split for case in suite.cases} == {"training", "validation", "test"}
    assert len({case.case_id for case in suite.cases}) == 5
    assert all("evidence" not in case.metadata for case in suite.cases)
    assert all(evidence[case.case_id].startswith("In this database") for case in suite.cases)
    second, _ = load_bird_mini_dev(data, databases)
    assert [(case.case_id, case.split) for case in suite.cases] == [
        (case.case_id, case.split) for case in second.cases
    ]


def test_bird_execution_accuracy_and_read_only_gate(tmp_path: Path):
    data, databases = _fixture(tmp_path)
    suite, evidence = load_bird_mini_dev(data, databases)
    case = suite.select("training")[0]
    evaluator = BirdMiniDevEvaluator(databases, evidence)

    def trace(sql: str) -> RolloutTrace:
        return RolloutTrace(case_id=case.case_id, split=case.split, input=case.input,
                            expected="", prediction=sql)

    assert evaluator.evaluate(case, trace("SELECT name FROM items WHERE active = 1")).score == 1.0
    assert evaluator.evaluate(case, trace("SELECT name FROM items")).score == 0.0
    assert evaluator.evaluate(case, trace("DELETE FROM items")).score == 0.0
    assert evaluator.evaluate(case, trace("ATTACH DATABASE ':memory:' AS other")).score == 0.0
    with sqlite3.connect(databases / "sample" / "sample.sqlite") as connection:
        assert connection.execute("SELECT count(*) FROM items").fetchone()[0] == 2


class _AgentProvider:
    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if "Use active = 1" in prompt:
            return "SELECT name FROM items WHERE active = 1"
        return "SELECT name FROM items"


class _ConsolidationProvider:
    def complete(self, prompt: str) -> str:
        records = json.loads(prompt.split("NEW EXPERIENCES:\n", 1)[1])
        return json.dumps({"decisions": [{
            "action": "create",
            "rationale": "Training feedback identifies a reusable status convention.",
            "evidence_ids": [record["experience_id"] for record in records],
            "note": {
                "note_id": "sample-active-status",
                "kind": "environment",
                "title": "Sample active status",
                "claim": "Active items have active = 1.",
                "trigger": "A question asks for active items in sample.",
                "guidance": ["Use active = 1."],
                "verification": ["Check the filtered result."],
                "applicability": ["sample database"],
                "limitations": [],
                "relation": "supports",
            },
        }]})


def test_bird_run_promotes_transfer_without_exposing_gold_sql(tmp_path: Path):
    data, databases = _fixture(tmp_path)
    agent = _AgentProvider()
    lock_path = tmp_path / "experiment.lock.json"
    lock_path.write_text(json.dumps(make_bird_mini_dev_lock(
        data, databases, limit_per_split=1
    )), encoding="utf-8")
    report = run_bird_mini_dev(
        tmp_path / "run", tmp_path / "wiki", data, databases,
        agent, _ConsolidationProvider(), limit_per_split=1, protocol_lock=lock_path,
    )

    assert report["baseline_validation_score"] == 0.0
    assert report["best_validation_score"] == 1.0
    assert report["baseline_test_score"] == 0.0
    assert report["raw_trace_test_score"] == 0.0
    assert report["test_score"] == 1.0
    assert report["accepted_skill"] == "bird-mini-dev-v1"
    assert all("SELECT name FROM items WHERE active = 1" not in prompt for prompt in agent.prompts)
    assert all("One means active" in prompt for prompt in agent.prompts)
    assert any("Raw training traces" in prompt for prompt in agent.prompts)
    raw = next((tmp_path / "wiki" / "evidence" / "raw").rglob("*.json"))
    assert "SELECT name FROM items WHERE active = 1" not in raw.read_text(encoding="utf-8")
    assert (tmp_path / "run" / "report.json").exists()
    assert (tmp_path / "run" / "protocol-lock.json").exists()
    assert (tmp_path / "run" / "run-config.json").exists()


def test_loader_rejects_missing_database(tmp_path: Path):
    data, _ = _fixture(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_bird_mini_dev(data, tmp_path / "missing")


def test_protocol_lock_freezes_public_inputs_and_selected_cases(tmp_path: Path):
    data, databases = _fixture(tmp_path)
    lock = make_bird_mini_dev_lock(data, databases, limit_per_split=1)
    suite, _ = load_bird_mini_dev(data, databases, limit_per_split=1)

    assert lock == make_bird_mini_dev_lock(data, databases, limit_per_split=1)
    assert lock["split_seed"] == "bird-mini-dev-v1"
    assert lock["cases"] == {
        split: [{"case_id": case.case_id, "db_id": "sample"} for case in suite.select(split)]
        for split in ("training", "validation", "test")
    }
    assert len(lock["database_files"]) == 2
    assert "SELECT name FROM items WHERE active = 1" not in json.dumps(lock)


def test_cli_generates_lock_without_model_configuration(tmp_path: Path):
    data, databases = _fixture(tmp_path)
    output = tmp_path / "run" / "experiment.lock.json"

    result = CliRunner().invoke(app, [
        "bird-mini-dev-lock", "--data", str(data), "--databases", str(databases),
        "--database-id", "sample", "--limit-per-split", "1", "--output", str(output),
    ])

    assert result.exit_code == 0, result.output
    assert json.loads(output.read_text(encoding="utf-8")) == make_bird_mini_dev_lock(
        data, databases, limit_per_split=1, database_id="sample"
    )


def test_run_rejects_changed_inputs_before_model_calls(tmp_path: Path):
    data, databases = _fixture(tmp_path)
    lock_path = tmp_path / "protocol-lock.json"
    lock_path.write_text(json.dumps(make_bird_mini_dev_lock(
        data, databases, limit_per_split=1
    )), encoding="utf-8")
    with sqlite3.connect(databases / "sample" / "sample.sqlite") as connection:
        connection.execute("INSERT INTO items VALUES ('three', 1)")
    agent = _AgentProvider()

    with pytest.raises(ValueError, match="Protocol lock differs"):
        run_bird_mini_dev(
            tmp_path / "run", tmp_path / "wiki", data, databases,
            agent, _ConsolidationProvider(), limit_per_split=1, protocol_lock=lock_path,
        )

    assert not agent.prompts
    assert not (tmp_path / "wiki").exists()
