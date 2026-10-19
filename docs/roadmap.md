# Beta roadmap

Updated 2026-10-10. The package's evolution engine, evaluation kernel, wiki, and skill
store remain task-neutral. BIRD Mini-Dev SQLite is the sole current benchmark adapter.
The old Blender/rustication, SVG, and text-normalization evaluation paths are no longer
part of this roadmap.

| Order | Milestone | Current state | Remaining work | Exit criterion |
| --- | --- | --- | --- | --- |
| 1 | Set the beta contract | The [beta contract](beta-contract.md) documents supported inputs, outputs, runtime, success/failure semantics, and a lock-and-run example. The CLI can create and verify a per-experiment lock of dataset/database hashes and selected case IDs offline. | Generate and check in a canonical lock from the upstream dataset, then verify the documented model run on that data. Model snapshots and dependency versions remain user-selected and recorded rather than globally pinned. | A new contributor can run the same example and identify every expected artifact and score. |
| 2 | Finish the clean transition | The CLI exposes BIRD plus general memory/skill commands; legacy evaluation code and assets have been removed; synthetic tests pass. | Commit or deliberately exclude the current untracked files and deletions. Test installation and the documented command from a clean checkout. Keep benchmark-specific logic in the BIRD adapter and audit docs for stale claims. | Clean checkout, repeatable install, accurate docs, green tests. |
| 3 | Validate the evaluation protocol | Local SQLite execution accuracy compares sets of result rows, with read-only execution and a timeout. Validation gates promotion; test is reported afterward. | Compare local grading with the official BIRD evaluator on representative cases. Record evaluator version, database hashes, selected case IDs, timeout, failures, and score denominator. Test answer/evidence isolation and repeatability explicitly. | Repeated evaluation agrees, invalid SQL fails clearly, and no validation/test oracle content enters memory or promotion. |
| 4 | Exercise the real learning path | A configured LLM runner, wiki consolidation, candidate skills, and no-skill/raw-trace/learned-skill test arms exist; tests use synthetic fixtures. | Run actual Mini-Dev data end to end. Preserve per-attempt prompts, outputs, evaluations, consolidation decisions, skill diffs, model configuration, and usage/cost data. Diagnose any failures before interpreting scores. | A documented real-data run completes with inspectable evidence, not just a fixture test. |
| 5 | Prove improvement, then harden | Validation-based promotion and a held-out test report are implemented. | Repeat runs to estimate variance; compare all three arms on identical test cases without tuning on test. Add model-call, runtime, token/cost, and artifact-size budgets, plus interruption recovery. Report negative results and regressions as clearly as gains. | A reproducible improvement with uncertainty reported, or a clear negative result, and actionable diagnostics for failed runs. |

The current split tests transfer of database-specific conventions to unseen questions
from the *same* database. It does not measure generalization to unseen databases and is
not an official BIRD leaderboard submission. See [benchmark protocol](benchmarks.md).
