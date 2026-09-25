# ADR 001: Self-improvement integration boundaries

- Status: Accepted
- Date: 2026-09-25

## Context

`algorithmic-historicism` needs skill evolution, trajectory distillation, and online candidate-skill creation while preserving domain ownership of Blender-centric architectural reconstruction.

## Decision summary

We will integrate external self-improvement systems through thin adapters instead of tightly coupling domain logic to any single research codebase.

### EvoSkill

- Intended reuse: candidate mutation/comparison lifecycle and benchmark-driven retention pattern.
- Integration choice: adapter (`src/algorithmic_historicism/integrations/evoskill.py`) that accepts repository-native skill packages and benchmark task collections.
- Rationale: retain swappable outer-loop machinery and avoid coupling accepted skill storage format to upstream benchmark assumptions.

### WikiSkill

- Intended reuse: trajectory-to-knowledge consolidation pattern preserving lessons from both successful and failed runs.
- Integration choice: local wiki adapter (`src/algorithmic_historicism/wiki/local.py`) plus optional external bridge (`src/algorithmic_historicism/integrations/wikiskill.py`).
- Rationale: markdown-based persistent wiki with explicit provenance is enough for MVP and keeps raw evidence separate from distilled claims.

### MUSE-Autoskill concepts

- Intended reuse: online missing-skill creation pattern during execution, followed by local testing and candidate registration.
- Integration choice: candidate skill lifecycle interface (`src/algorithmic_historicism/skills/candidates.py`) and optional bridge (`src/algorithmic_historicism/integrations/muse.py`).
- Rationale: preserve repository ownership of executable Blender skill artifacts while supporting future external automation.

## Dependency policy

For all three ecosystems we require before direct code import:

1. compatible OSS license,
2. acceptable maintenance status,
3. stable Python API surface,
4. low coupling to original benchmark/task domain,
5. ability to substitute this repository's evaluator and task model.

If any check fails, we adapt only minimal algorithmic patterns behind stable adapters.

## Consequences

- Domain architecture remains explicit and testable.
- External implementations stay replaceable.
- Skills and wiki knowledge remain durable repository-native artifacts.
