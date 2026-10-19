# ADR 001: Self-improvement integration boundaries

- Status: Superseded by the task-neutral engine and BIRD adapter
- Date: 2026-09-25

## Context

This decision recorded an earlier architecture-specific scaffold and mock external adapters.
The current package keeps task execution and grading behind the protocols in
`evolution/engine.py`. The BIRD Mini-Dev adapter lives in `evolution/bird_mini_dev.py`.

## Decision summary

We keep benchmark-specific data handling outside the evolution engine. Wiki evidence, note
revision, candidate skills, and promotion remain local package responsibilities.

## Current implementation

- `EvolutionEngine` coordinates task-provided runners, evaluators, wiki maintainers, and
  skill proposers. Promotion uses validation; test results are for reporting only.
- `WikiWorkspace` stores immutable training traces, curated notes with evidence links,
  revisions, candidate metadata, and accepted skills.
- `bird_mini_dev.py` reads official BIRD Mini-Dev SQLite rows and databases, hides gold SQL
  from the runner, and grades with BIRD's execution-accuracy rule. It does not import the
  upstream batch evaluator or claim leaderboard comparability.
- The former domain-specific scaffolds and mock external integrations have been removed.

## Consequences

- New benchmark adapters can provide their own task and grading logic without changing the
  shared engine.
- Wiki knowledge and skills remain durable repository-native artifacts.
