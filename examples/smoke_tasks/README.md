# Smoke tasks

Twelve small, original Harbor tasks for checking that the evaluation pipeline works end to end:
image build, agent run, verifier, reward file, result collection.

**These are a pipeline check, not a capability benchmark.** They are tiny and the reference solutions
(`solution/solve.sh`) are public in this repository. Therefore:

- never report results on them as held-out or as evidence of agent capability;
- never use them, their solutions or agent trajectories on them for training.

## Layout

```
tasks/<name>/
  task.toml          metadata (category, difficulty, smoke = true), 1 CPU, 1024 MB
  instruction.md     what the agent is told
  environment/       Dockerfile (+ app/ starter files copied to /app)
  tests/             test.sh + verify.py, mounted at /tests only when the verifier runs
  solution/solve.sh  reference solution, used by the oracle agent
```

All images use the same base, `python:3.12-slim` pinned by digest. Tests and solutions are not copied into the
image. The verifier needs no network: it runs `tests/verify.py` (standard library only) against hidden inputs and
writes `1` or `0` to `/logs/verifier/reward.txt`. Building the `ahl-git-revert` image needs network once
(`apt-get install git`).

## Running

Oracle (reference solution; every task should score 1.0):

```bash
harbor run -p examples/smoke_tasks/tasks -a oracle -n 4 -o /path/to/jobs --job-name smoke-oracle
```

Nop (agent does nothing; every task should score 0.0):

```bash
harbor run -p examples/smoke_tasks/tasks -a nop -n 4 -o /path/to/jobs --job-name smoke-nop
```

Checked with Harbor 0.25.0 (the project pin) and 0.27.0. Use `-i 'ahl-fix-*'` to select tasks by name.

## Tasks

| Task | Category | Difficulty | What the agent does |
|---|---|---|---|
| `ahl-fix-median` | debugging | easy | fix a buggy `median` (even length, mutation, empty input) |
| `ahl-fix-failing-test` | debugging | easy | make a failing unittest pass by fixing discount rounding |
| `ahl-fix-duration-parse` | debugging | medium | fix a duration parser (`d`, `ms`, spaces, invalid input) |
| `ahl-json-flatten` | data-processing | easy | write a CLI that flattens nested JSON |
| `ahl-jsonl-dedupe` | data-processing | easy | write a CLI that dedupes JSON Lines by id, last record wins |
| `ahl-csv-aggregate` | data-processing | medium | write a CLI that sums CSV amounts per region with exact decimals |
| `ahl-markdown-toc` | text-processing | medium | generate a Markdown table of contents with anchors |
| `ahl-shell-rotate` | shell-scripting | medium | bash log-rotation script (keep newest N) |
| `ahl-shell-env-merge` | shell-scripting | medium | bash script merging `.env`-style files |
| `ahl-log-top-5xx` | log-analysis | medium | summarise an access log: top client IPs by 5xx responses |
| `ahl-refactor-report` | refactoring | medium | split a monolithic `main` into importable functions, same output |
| `ahl-git-revert` | git | medium | undo a bad commit with `git revert`, keep history |
