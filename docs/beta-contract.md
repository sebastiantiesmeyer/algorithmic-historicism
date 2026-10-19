# Beta contract

This is the supported BIRD Mini-Dev SQLite workflow for the current beta. The shared
engine, wiki, and skill APIs are task-neutral; this document describes the one current
benchmark adapter. This is a custom within-database learning experiment, not an official
BIRD leaderboard submission.

## Runtime and inputs

- Python 3.11 or newer and the dependency ranges in `pyproject.toml` are required. No
  Blender installation is needed.
- The CLI uses an OpenAI Responses API-compatible endpoint. Set `OPENAI_API_KEY` and
  `AH_AGENT_MODEL`; `AH_CONSOLIDATOR_MODEL` defaults to the agent model. The model must
  return text. There is no fixed model version: choose a stable model ID or snapshot for
  comparisons and retain `run-config.json`. A model alias can change independently of
  this repository. `AH_LLM_BASE_URL`, `AH_LLM_MAX_OUTPUT_TOKENS`, and
  `AH_LLM_TEMPERATURE` are optional; see `.env.example`.
- `--data` accepts a UTF-8 JSON array or JSONL file with `question_id`, `db_id`,
  `question`, and `SQL` on each row. `evidence` and `difficulty` are optional. The
  canonical input is `mini_dev_sqlite.json` from BIRD Mini-Dev; benchmark data is not
  included in this repository.
- `--databases` points to SQLite files at `<root>/<db_id>/<db_id>.sqlite` or
  `<root>/<db_id>.sqlite`. Column descriptions in
  `<root>/<db_id>/database_description/*.csv` are included in prompts when present.
  Each selected database needs at least three questions. Database IDs may contain only
  letters, digits, `_`, and `-`.
- Use a fresh `--wiki` and `--workspace` for an independent run. A reused wiki may
  supply an accepted skill and accumulated notes; its validation baseline is then not
  a no-skill baseline.

## Frozen split

The adapter groups questions by database, sorts each group by the SHA-256 digest of
`bird-mini-dev-v1:<question_id>`, and assigns approximately 60% to training, 20% to
validation, and 20% to test. `--limit-per-split` takes the first N from each split and
database; `0` means no limit. Validation can admit a skill; test is evaluated only
after that decision. The split tests transfer to unseen questions from the *same*
database, not generalization to unseen databases.

`bird-mini-dev-lock` runs without a model. Its JSON records the dataset hash, hashes
of each selected SQLite file and description CSV, split seed and method, parameters,
and the selected `(db_id, question_id)` pairs. It contains no questions, gold SQL, or
evidence. Keep this file with the experiment. Pass it back with `--lock` to reject
changed data, database contents, descriptions, or selected cases before any model call.
The lock does not freeze model behavior or package dependencies.

## Example

After installing the package and downloading the official SQLite data, adjust these
paths and choose a database ID present in your copy:

```powershell
$data = "path/to/mini_dev_sqlite.json"
$databases = "path/to/dev_databases"
$db = "your_db_id"
$run = "runs/bird-example"

algorithmic-historicism bird-mini-dev-lock `
  --data $data --databases $databases --database-id $db `
  --limit-per-split 10 --output "$run/experiment.lock.json"

algorithmic-historicism bird-mini-dev `
  --data $data --databases $databases --database-id $db `
  --limit-per-split 10 --lock "$run/experiment.lock.json" `
  --workspace $run --wiki "memory/bird-example"
```

Lock generation validates the inputs and selected split without an API key. The second
command needs the configured model endpoint and may incur API charges. Do not reuse
the example workspace for another run: training traces are immutable and runs are not
resumable yet.

## Outputs and success

| Path | Meaning |
| --- | --- |
| `<workspace>/protocol-lock.json` | The exact public input and case manifest used by the run, written before model calls. |
| `<workspace>/run-config.json` | Dataset hash, split seed, selection parameters, iteration limit, and configured model IDs/settings. Written after a complete run. |
| `<workspace>/report.json` | Validation history and mean execution accuracy for no-skill, raw-trace, and learned-skill test conditions. Written after a complete run. |
| `<workspace>/candidates/` | Proposed skill documents and validation decisions, if a proposal was made. |
| `<wiki>/evidence/raw/` | Training attempt traces and their evaluation feedback. Validation/test traces are not persisted here. |
| `<wiki>/strategies/`, `antipatterns/`, `environment/`, `skills/` | Curated notes and accepted skills when consolidation or promotion produces them. |

Exit code 0 with `report.json` and `run-config.json` means the selected protocol
completed. If no skill is accepted, `test_score` equals `baseline_test_score` without
an additional learned-skill model call. A score is the fraction of selected cases whose
predicted SQL returns the same *set* of rows as gold SQL on the selected database;
invalid or timed-out predicted SQL receives zero. Successful execution does not mean
that a skill improved accuracy or that a query is semantically equivalent on other
data. Model/API errors and invalid gold SQL abort the run; partial artifacts may remain.
Prompt and token/cost capture, interruption recovery, and official evaluator parity
are not part of this contract yet.
