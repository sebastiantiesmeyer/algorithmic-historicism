from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .config import LLMSettings
from .evolution.bird_mini_dev import make_bird_mini_dev_lock, run_bird_mini_dev
from .llm.providers.openai import openai_provider


class ExperimentLLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    agent_model: str = Field(min_length=1)
    consolidator_model: str | None = Field(default=None, min_length=1)
    max_output_tokens: int = Field(default=12_000, ge=1, strict=True)
    temperature: float | None = Field(default=None, ge=0, le=2)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal[1] = 1
    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)
    benchmark: Literal["bird-mini-dev"] = "bird-mini-dev"
    data: Path
    databases: Path
    database_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$")
    wiki: Path
    runs: Path
    lock: Path | None = None
    env_file: Path = Path(".env")
    limit_per_split: int = Field(default=3, ge=0, strict=True)
    max_iterations: int = Field(default=1, ge=1, strict=True)
    llm: ExperimentLLMConfig

    @classmethod
    def load(cls, path: Path) -> "ExperimentConfig":
        path = path.resolve()
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid experiment YAML: {path}") from exc
        config = cls.model_validate(payload)
        for field in ("data", "databases", "wiki", "runs", "env_file", "lock"):
            value = getattr(config, field)
            if value is not None:
                setattr(config, field, (path.parent / value.expanduser()).resolve())
        if config.lock is None:
            config.lock = path.with_suffix(".lock.json")
        return config

    def protocol(self) -> dict[str, object]:
        return make_bird_mini_dev_lock(
            self.data, self.databases, limit_per_split=self.limit_per_split or None,
            database_id=self.database_id,
        )


def lock_experiment(path: Path) -> Path:
    config = ExperimentConfig.load(path)
    protocol = config.protocol()
    input_paths = {path.resolve(), config.data}
    input_paths.update(config.databases / item["path"] for item in protocol["database_files"])
    if config.lock in input_paths:
        raise ValueError("Protocol lock must use a separate file from the configuration and benchmark inputs")
    config.lock.parent.mkdir(parents=True, exist_ok=True)
    config.lock.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    return config.lock


def run_experiment(path: Path) -> tuple[Path, dict[str, object]]:
    config = ExperimentConfig.load(path)
    if not config.lock.is_file():
        raise ValueError("Experiment lock is missing; run 'experiment lock' first")
    if json.loads(config.lock.read_text(encoding="utf-8")) != config.protocol():
        raise ValueError("Protocol lock differs from the selected cases or input files")
    settings = LLMSettings.from_env(
        config.env_file, model_overrides=config.llm.model_dump()
    )
    common = {
        "api_key": settings.api_key, "base_url": settings.base_url,
        "max_output_tokens": settings.max_output_tokens, "temperature": settings.temperature,
    }
    agent = openai_provider(model=settings.agent_model, **common)
    consolidator = openai_provider(model=settings.consolidator_model, **common)
    run_id = f"{config.name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}-{uuid4().hex[:8]}"
    workspace = config.runs / run_id
    workspace.mkdir(parents=True, exist_ok=False)
    snapshot = config.model_dump(mode="json")
    snapshot["llm"] = settings.metadata()
    snapshot["config_file"] = str(path.resolve())
    snapshot["workspace"] = str(workspace)
    (workspace / "resolved-experiment.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8"
    )
    report = run_bird_mini_dev(
        workspace, config.wiki, config.data, config.databases, agent, consolidator,
        limit_per_split=config.limit_per_split or None, database_id=config.database_id,
        max_iterations=config.max_iterations, protocol_lock=config.lock,
        run_metadata={"llm": settings.metadata(), "experiment": snapshot},
    )
    return workspace, report
