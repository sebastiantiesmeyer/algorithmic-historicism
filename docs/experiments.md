# Experiment configuration

An experiment configuration defines one persistent learning history. Each invocation
creates a new run directory and uses the configured wiki. Use a separate wiki for an
independent comparison. This optimizes wiki knowledge and skill instructions, not model
weights. BIRD Mini-Dev SQLite is the current benchmark adapter.

## Linux/WSL quick start

From the repository directory, after installing the package and downloading BIRD data:

```bash
cp experiment.example.yaml experiment.yaml
test -f .env || cp .env.example .env
# Edit .env: set OPENAI_API_KEY.
# Edit experiment.yaml: set data, databases, and llm.agent_model.
algorithmic-historicism experiment lock experiment.yaml
algorithmic-historicism experiment run experiment.yaml
```

The first command is offline and does not initialize the wiki. The second verifies the
lock before creating providers or making model calls. It prints the report and the new
workspace path when it completes. Existing direct `bird-mini-dev` commands still work.

## Fields

YAML and JSON use the same schema. Unknown fields are rejected at both levels.
All relative paths resolve against the configuration file's directory, regardless of
the shell's current directory. Absolute paths and `~` paths are supported. Under WSL,
use Linux paths, such as `/mnt/c/...` for data on a Windows drive.

| Field | Required/default | Meaning |
| --- | --- | --- |
| `schema_version` | `1` | Configuration schema version. |
| `name` | Required | Up to 64 lowercase letters, digits, and separating hyphens; prefixes run directory names. |
| `benchmark` | `bird-mini-dev` | Currently the only supported benchmark. |
| `data` | Required | Mini-Dev SQLite questions JSON or JSONL file. |
| `databases` | Required | Root containing SQLite databases and optional descriptions. |
| `database_id` | All databases | Restrict the selected cases to one database. |
| `wiki` | Required | Persistent wiki path, reused across runs. |
| `runs` | Required | Parent directory for unique run subdirectories. |
| `lock` | Config basename + `.lock.json` | Protocol lock path; e.g. `study.yaml` uses `study.lock.json`. |
| `env_file` | `.env` | Credential/endpoint environment file. |
| `limit_per_split` | `3` | Maximum cases per split and database; `0` means all. |
| `max_iterations` | `1` | Maximum training/consolidation/proposal iterations per run. |
| `llm.agent_model` | Required | Model used to answer tasks. |
| `llm.consolidator_model` | Agent model | Model used to curate wiki notes. |
| `llm.max_output_tokens` | `12000` | Positive output-token limit per call. |
| `llm.temperature` | `null` | Optional value from 0 to 2; null omits the API parameter. |

The experiment file controls model IDs and generation settings. `AH_AGENT_MODEL`,
`AH_CONSOLIDATOR_MODEL`, `AH_LLM_MAX_OUTPUT_TOKENS`, and `AH_LLM_TEMPERATURE` do not
override it. `OPENAI_API_KEY`, optional `AH_LLM_BASE_URL`, and `AH_LLM_PROVIDER=openai`
come from the shell environment or `env_file`; existing environment variables take
precedence over that file. Credentials are not accepted as experiment fields and are
excluded from saved configuration snapshots.

## Locks and run artifacts

The configuration expresses intent. The separate protocol lock records exact input
hashes and selected cases. `experiment lock` regenerates the configured lock; run it
deliberately when changing data, database selection, or case limits. Model settings and
iteration counts can change without changing this data lock. A lock does not freeze
the evolving wiki, model service, or dependencies.

Each `experiment run` creates `<runs>/<name>-<UTC timestamp>-<random suffix>/`.
Before learning starts, it saves the resolved paths, effective model settings, source
configuration path, and workspace path in `resolved-experiment.json`. The same
configuration is included in `run-config.json`. The existing [beta contract](beta-contract.md)
describes attempt journals, status, report, and wiki artifacts.

To continue learning, rerun the command with the same configuration and wiki. It starts
a new run, loads the active skill, and revisits the selected training cases. Its validation
baseline can therefore already include learned knowledge. It does not resume interrupted
attempts. Use a fresh wiki path for an independent baseline, and avoid simultaneous
runs against the same wiki.

Inspect a completed run using the workspace path printed by the command:

```bash
cat runs/student-club-first/<run-directory>/report.json
algorithmic-historicism memory list --wiki memory/student-club-first
algorithmic-historicism skills list --wiki memory/student-club-first
```

No accepted skill is a valid outcome: proposals must improve validation accuracy before
promotion. Three test questions exercise the workflow but cannot establish a reliable gain.
