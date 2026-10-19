# algorithmic-historicism

This package studies whether evaluated agent attempts can become a persistent wiki and then
reusable procedural skills. Its evolution engine, evaluation kernel, wiki, and skill store are
task-neutral. BIRD Mini-Dev SQLite is the current benchmark adapter.

## Setup

```powershell
python -m venv .venv
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` and `AH_AGENT_MODEL` in `.env`. `AH_CONSOLIDATOR_MODEL` is optional.

Download the canonical BIRD Mini-Dev SQLite questions and databases from the
[BIRD Mini-Dev release](https://github.com/bird-bench/mini_dev). The adapter expects
`mini_dev_sqlite.json` (or JSONL) and a database root containing files such as
`dev_databases/<db_id>/<db_id>.sqlite`. Benchmark data is not vendored here.

Generate a protocol lock offline, then use it for the model run:

```powershell
algorithmic-historicism bird-mini-dev-lock `
  --data path/to/mini_dev_sqlite.json `
  --databases path/to/dev_databases `
  --database-id student_club `
  --limit-per-split 10 `
  --output runs/bird-example/experiment.lock.json
```

```powershell
algorithmic-historicism bird-mini-dev `
  --data path/to/mini_dev_sqlite.json `
  --databases path/to/dev_databases `
  --database-id student_club `
  --limit-per-split 10 `
  --lock runs/bird-example/experiment.lock.json `
  --workspace runs/bird-example `
  --wiki memory/bird-example
```

Omit `--database-id` to include every database. `--limit-per-split` applies to each database;
pass `0` to use every case. The default is ten cases per split and database. The command
evaluates validation before and after training, consolidates only training feedback, promotes
skills only on validation improvement, then evaluates test with no skill, retrieved raw
training traces, and the learned skill. Test results do not affect promotion. Its report is saved under
`runs/bird-mini-dev-*/report.json` by default. The run is a custom continual-learning split,
not an official BIRD leaderboard submission.

The BIRD adapter uses BIRD's execution-accuracy rule: predicted and gold SQL must return the
same set of rows. It executes read-only SQLite with a time limit. Gold SQL and oracle evidence
are kept out of agent prompts; schema and column descriptions are public context, and training
evidence may enter the wiki after an attempt. See
[benchmark protocol](docs/benchmarks.md) for limitations and comparison requirements.
The [beta contract](docs/beta-contract.md) defines supported inputs, artifacts, success,
and failure behavior.
The [beta roadmap](docs/roadmap.md) tracks the remaining work.

## Core

The shared engine accepts a task runner, evaluator, wiki maintainer, and skill proposer. It
stores training traces in `evidence/`, notes in `strategies/`, `antipatterns/`, and
`environment/`, and accepted skills in `skills/`. The test split is evaluated only after
promotion decisions. The CLI also provides `memory init|list|search|show|approve|deprecate|pin`
and `skills list`, each with an explicit `--wiki` path.

```powershell
python -m pytest
```
