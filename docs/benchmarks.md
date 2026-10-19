# BIRD Mini-Dev protocol

The current adapter reads the official [BIRD Mini-Dev SQLite data](https://github.com/bird-bench/mini_dev)
and its database files. It does not copy benchmark data into this repository. BIRD's data is
licensed CC BY-SA 4.0; cite the upstream benchmark when publishing results.

## Custom split

Within each database, question IDs are sorted by a stable hash and assigned 60% training,
20% validation, and 20% test. `--limit-per-split` selects the first N cases in each split.
This creates repeated exposure to a database's conventions while keeping questions disjoint.
The fixed split is a local transfer experiment, not the official Mini-Dev split or leaderboard.

The agent receives the question, SQLite schema, column descriptions when available, and current accepted skill. The gold SQL and
the annotated `evidence` field remain grader-only until a training attempt has been scored.
Training evidence can then be distilled into wiki notes. Validation and test evidence never
enters the wiki. The candidate skill is evaluated on validation and promoted only for a strict
improvement. After decisions are final, test is scored with no skill, retrieved raw training
traces from the same database, and the learned skill.

## Scoring and limits

The per-case score follows the official [BIRD EX evaluator](https://github.com/bird-bench/mini_dev/blob/main/evaluation/evaluation_ex.py):
execute predicted and gold SQL on the same SQLite database and compare sets of returned rows.
The local adapter adds a read-only authorizer and query time limit. This is compatible with
the EX rule but is not an invocation of the official batch evaluator. A single database can
admit accidental matches, so the score is an imperfect proxy for query equivalence.

The three held-out conditions use the same questions and model. The report compares their
execution accuracy. Repeated stochastic runs, token and time accounting, and official
leaderboard export are not yet implemented.
