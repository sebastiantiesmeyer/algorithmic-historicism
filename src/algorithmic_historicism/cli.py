from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer

from .config import LLMSettings
from .evolution.bird_mini_dev import make_bird_mini_dev_lock, run_bird_mini_dev
from .llm.providers.openai import openai_provider
from .skills.registry import SkillRegistry
from .wiki.workspace import WikiWorkspace

app = typer.Typer(help="Experience, wiki memory, and skill evolution")
skills_app = typer.Typer(help="Inspect accepted skills")
memory_app = typer.Typer(help="inspect and curate persistent wiki memory")
app.add_typer(skills_app, name="skills")
app.add_typer(memory_app, name="memory")


@app.command("bird-mini-dev")
def bird_mini_dev(
    data: Path = typer.Option(..., "--data", help="Official mini_dev_sqlite.json or JSONL."),
    databases: Path = typer.Option(..., "--databases", help="Root of official SQLite databases."),
    wiki: Path = typer.Option(..., "--wiki"),
    workspace: Path | None = typer.Option(None, "--workspace"),
    env_file: Path = typer.Option(Path(".env"), "--env-file"),
    limit_per_split: int = typer.Option(10, "--limit-per-split", min=0),
    database_id: str | None = typer.Option(None, "--database-id"),
    max_iterations: int = typer.Option(1, "--max-iterations", min=1),
    lock: Path | None = typer.Option(None, "--lock", help="Require inputs and cases to match this lock."),
):
    """Run a custom continual-learning protocol on BIRD Mini-Dev SQLite."""
    try:
        settings = LLMSettings.from_env(env_file)
        common = {
            "api_key": settings.api_key,
            "base_url": settings.base_url,
            "max_output_tokens": settings.max_output_tokens,
            "temperature": settings.temperature,
        }
        target = workspace or Path("runs") / f"bird-mini-dev-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        report = run_bird_mini_dev(
            target, wiki, data, databases,
            openai_provider(model=settings.agent_model, **common),
            openai_provider(model=settings.consolidator_model, **common),
            limit_per_split=limit_per_split or None,
            database_id=database_id,
            max_iterations=max_iterations,
            protocol_lock=lock,
            run_metadata={"llm": settings.metadata()},
        )
    except (ValueError, FileNotFoundError, TypeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(report, indent=2))
    typer.echo(f"workspace: {target}")


@app.command("bird-mini-dev-lock")
def bird_mini_dev_lock(
    data: Path = typer.Option(..., "--data", help="Official mini_dev_sqlite.json or JSONL."),
    databases: Path = typer.Option(..., "--databases", help="Root of official SQLite databases."),
    output: Path = typer.Option(..., "--output", help="Where to write the protocol lock."),
    limit_per_split: int = typer.Option(10, "--limit-per-split", min=0),
    database_id: str | None = typer.Option(None, "--database-id"),
):
    """Freeze BIRD input hashes and selected cases without calling a model."""
    try:
        lock = make_bird_mini_dev_lock(
            data, databases,
            limit_per_split=limit_per_split or None,
            database_id=database_id,
        )
    except (ValueError, FileNotFoundError, TypeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    typer.echo(str(output))


@memory_app.command("init")
def initialize_memory(wiki: Path = typer.Option(..., "--wiki")):
    workspace = WikiWorkspace.open(wiki, create=True)
    typer.echo(str(workspace.root))


@memory_app.command("list")
def list_memory(
    wiki: Path = typer.Option(..., "--wiki"),
    kind: str | None = typer.Option(None, "--kind"),
    include_archived: bool = typer.Option(False, "--include-archived"),
):
    workspace = WikiWorkspace.open(wiki, create=True)
    notes = workspace.list_notes(include_archived=include_archived)
    if kind:
        if kind not in {"strategy", "antipattern", "environment"}:
            raise typer.BadParameter("kind must be strategy, antipattern, or environment")
        notes = [note for note in notes if note.kind == kind]
    for note in notes:
        typer.echo(f"{note.note_id}\t{note.kind}\t{note.status}\t{note.title}")


@memory_app.command("search")
def search_memory(
    query: str,
    wiki: Path = typer.Option(..., "--wiki"),
    limit: int = typer.Option(5, "--limit", min=1, max=50),
):
    workspace = WikiWorkspace.open(wiki, create=True)
    for note in workspace.search(query, limit=limit):
        typer.echo(f"{note.note_id}\t{note.kind}\t{note.status}\t{note.title}")


@memory_app.command("show")
def show_memory(note_id: str, wiki: Path = typer.Option(..., "--wiki")):
    workspace = WikiWorkspace.open(wiki, create=True)
    note = workspace.find_note(note_id)
    if note is None:
        raise typer.BadParameter(f"unknown note: {note_id}")
    typer.echo(workspace.render_note(note))


def _edit_memory_note(wiki: Path, note_id: str, *, status: str | None = None, pinned: bool | None = None):
    workspace = WikiWorkspace.open(wiki, create=True)
    note = workspace.find_note(note_id)
    if note is None:
        raise typer.BadParameter(f"unknown note: {note_id}")
    if status is not None:
        note.status = status
    if pinned is not None:
        note.pinned = pinned
    workspace.upsert_note(note, actor="human")
    typer.echo(f"{note.note_id}\t{note.status}\tpinned={str(note.pinned).lower()}")


@memory_app.command("approve")
def approve_memory(note_id: str, wiki: Path = typer.Option(..., "--wiki")):
    _edit_memory_note(wiki, note_id, status="accepted")


@memory_app.command("deprecate")
def deprecate_memory(note_id: str, wiki: Path = typer.Option(..., "--wiki")):
    _edit_memory_note(wiki, note_id, status="deprecated")


@memory_app.command("pin")
def pin_memory(
    note_id: str,
    wiki: Path = typer.Option(..., "--wiki"),
    remove: bool = typer.Option(False, "--remove", help="Remove the pin."),
):
    _edit_memory_note(wiki, note_id, pinned=not remove)


@skills_app.command("list")
def list_skills(wiki: Path = typer.Option(..., "--wiki")):
    registry = SkillRegistry(WikiWorkspace.open(wiki, create=True).skills_dir)
    for skill in registry.list_accepted():
        typer.echo(skill.name)


if __name__ == "__main__":
    app()
