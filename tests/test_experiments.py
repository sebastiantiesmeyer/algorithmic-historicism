import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from algorithmic_historicism.cli import app
from algorithmic_historicism.experiments import ExperimentConfig
from algorithmic_historicism import experiments


@pytest.fixture
def experiment_file(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    databases = root / "databases" / "sample"
    databases.mkdir(parents=True)
    with sqlite3.connect(databases / "sample.sqlite") as connection:
        connection.execute("CREATE TABLE items (name TEXT)")
        connection.execute("INSERT INTO items VALUES ('one')")
    (root / "questions.json").write_text(json.dumps([
        {"question_id": index, "db_id": "sample", "question": f"List names {index}",
         "SQL": "SELECT name FROM items"}
        for index in range(10)
    ]), encoding="utf-8")
    payload = {
        "name": "first-learning", "benchmark": "bird-mini-dev",
        "data": "questions.json", "databases": "databases", "database_id": "sample",
        "wiki": "memory", "runs": "runs", "limit_per_split": 1,
        "llm": {"agent_model": "agent", "consolidator_model": "memory"},
    }
    path = root / "experiment.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_paths_are_relative_to_configuration_from_any_cwd(experiment_file: Path, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ExperimentConfig.load(experiment_file)
    assert config.data == experiment_file.parent / "questions.json"
    assert config.wiki == experiment_file.parent / "memory"
    assert config.runs == experiment_file.parent / "runs"
    assert config.env_file == experiment_file.parent / ".env"
    assert config.lock == experiment_file.with_suffix(".lock.json")


@pytest.mark.parametrize("patch", [
    {"typo": True}, {"max_iterations": 0}, {"limit_per_split": -1},
    {"limit_per_split": True}, {"max_iterations": "3"}, {"name": "../outside"},
    {"benchmark": "unknown"}, {"llm": {"agent_model": "agent", "temprature": 1}},
    {"llm": {"agent_model": " "}}, {"llm": {"agent_model": "agent", "api_key": "secret"}},
])
def test_invalid_config_rejected(experiment_file: Path, patch: dict):
    payload = yaml.safe_load(experiment_file.read_text())
    payload.update(patch)
    experiment_file.write_text(yaml.safe_dump(payload))
    with pytest.raises(ValidationError):
        ExperimentConfig.load(experiment_file)


def test_json_config_and_custom_lock(experiment_file: Path):
    payload = yaml.safe_load(experiment_file.read_text())
    payload.update({"lock": "locks/inputs.json", "limit_per_split": 0})
    path = experiment_file.with_suffix(".json")
    path.write_text(json.dumps(payload))
    config = ExperimentConfig.load(path)
    assert config.lock == path.parent / "locks/inputs.json"
    assert len(config.protocol()["cases"]["training"]) == 6


def test_lock_is_offline_and_does_not_create_wiki(experiment_file: Path, monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("Offline lock must not create a provider")

    monkeypatch.setattr(experiments, "openai_provider", forbidden)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = CliRunner().invoke(app, ["experiment", "lock", str(experiment_file)])
    assert result.exit_code == 0, result.output
    config = ExperimentConfig.load(experiment_file)
    assert json.loads(config.lock.read_text()) == config.protocol()
    assert not config.wiki.exists()
    assert not config.runs.exists()


@pytest.mark.parametrize("lock_path", ["experiment.yaml", "questions.json", "databases/sample/sample.sqlite"])
def test_lock_cannot_overwrite_inputs(experiment_file: Path, lock_path: str):
    payload = yaml.safe_load(experiment_file.read_text())
    payload["lock"] = lock_path
    experiment_file.write_text(yaml.safe_dump(payload))
    target = experiment_file.parent / lock_path
    original = target.read_bytes()
    with pytest.raises(ValueError, match="separate file"):
        experiments.lock_experiment(experiment_file)
    assert target.read_bytes() == original


@pytest.mark.parametrize("changed", [False, True])
def test_missing_or_changed_lock_rejected_before_providers(experiment_file: Path, monkeypatch, changed: bool):
    if changed:
        experiments.lock_experiment(experiment_file)
        config = ExperimentConfig.load(experiment_file)
        config.data.write_text(config.data.read_text() + "\n")

    def forbidden(**kwargs):
        pytest.fail("Invalid lock must be rejected before provider creation")

    monkeypatch.setattr(experiments, "openai_provider", forbidden)
    result = CliRunner().invoke(app, ["experiment", "run", str(experiment_file)])
    assert result.exit_code != 0
    assert "lock" in result.output.lower()
    assert not ExperimentConfig.load(experiment_file).runs.exists()


def test_cli_runs_use_new_directories_same_wiki_and_record_resolved_settings(
    experiment_file: Path, tmp_path: Path, monkeypatch,
):
    # Credentials/endpoint come from the config-adjacent .env, models from YAML.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AH_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AH_AGENT_MODEL", "ignored-env-model")
    monkeypatch.setenv("AH_LLM_MAX_OUTPUT_TOKENS", "ignored-invalid-value")
    monkeypatch.setenv("AH_LLM_TEMPERATURE", "ignored-invalid-value")
    monkeypatch.delenv("AH_LLM_BASE_URL", raising=False)
    (experiment_file.parent / ".env").write_text(
        "OPENAI_API_KEY=test-secret\nAH_LLM_BASE_URL=https://example.invalid/v1\n"
    )
    calls = []

    class Provider:
        def __init__(self, model):
            self.model = model

        def complete(self, prompt):
            return '{"decisions": []}' if self.model == "memory" else "SELECT name FROM items"

    def provider(**kwargs):
        calls.append(kwargs)
        return Provider(kwargs["model"])

    monkeypatch.setattr(experiments, "openai_provider", provider)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["experiment", "lock", str(experiment_file)]).exit_code == 0
    for _ in range(2):
        result = runner.invoke(app, ["experiment", "run", str(experiment_file)])
        assert result.exit_code == 0, result.output
    config = ExperimentConfig.load(experiment_file)
    workspaces = sorted(config.runs.iterdir())
    assert len(workspaces) == 2
    for workspace in workspaces:
        snapshot_text = (workspace / "resolved-experiment.json").read_text()
        assert "test-secret" not in snapshot_text
        snapshot = json.loads(snapshot_text)
        assert snapshot["wiki"] == str(config.wiki)
        assert snapshot["workspace"] == str(workspace)
        assert snapshot["llm"]["agent_model"] == "agent"
        report = json.loads((workspace / "report.json").read_text())
        assert report["test_score"] == 1.0
        assert "test-secret" not in (workspace / "run-config.json").read_text()
    assert len(list((config.wiki / "evidence/raw").iterdir())) == 2
    assert [call["model"] for call in calls] == ["agent", "memory", "agent", "memory"]
    assert all(call["api_key"] == "test-secret" for call in calls)
    assert all(call["base_url"] == "https://example.invalid/v1" for call in calls)
    assert all(call["max_output_tokens"] == 12000 and call["temperature"] is None for call in calls)
