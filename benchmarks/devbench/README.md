# devbench: a development coding benchmark

30 Harbor tasks built from six permissively licensed Python repositories at pinned commits. They are for
**development decisions** in this project: comparing harnesses, adapters and serving settings. They are not
SWE-bench, not a held-out test set, and results on them must not be reported as either. Never train on them.

Dataset config: [`configs/datasets/devbench.yaml`](../../configs/datasets/devbench.yaml) (split `validation`).

## Sources and licences

| Key | Repository | Commit | Licence (checked in the file at that commit) |
|---|---|---|---|
| markdown | Python-Markdown/markdown | `27c014198021f71442301319981a3ed366ae2ad1` | BSD-3-Clause (`LICENSE.md`) |
| tablib | jazzband/tablib | `b6a75dcbe01cc42b3fd45ae5005901e2639fa7a7` | MIT (`LICENSE`) |
| more-itertools | more-itertools/more-itertools | `aa9977698a5e6ae15d3fdfac08a5fc5621c4e179` | MIT (`LICENSE`) |
| jmespath | jmespath/jmespath.py | `2812594e69d43098ef60f81f4efc404c071b0418` | MIT (`LICENSE`) |
| semver | python-semver/python-semver | `a4b7d337b1eb699ad4bad532a4b3fc68f8ec2408` | BSD-3-Clause (`LICENSE.txt`) |
| itsdangerous | pallets/itsdangerous | `672971d66a2ef9f85151e53283113f33d642dabd` | BSD-3-Clause (`LICENSE.txt`) |

Each upstream repository was checked individually; the SWE-smith tool's own MIT licence was not relied on.
Task images download the GitHub source archive of the pinned commit and check its sha256
([`repos.json`](repos.json)), so upstream source is not stored here. The tasks store small upstream excerpts
(bug patches, reference solutions) and a copy of each repository's tests inside the verifier
(`tests/restore.tar.gz`) together with that repository's licence (`tests/UPSTREAM_LICENSE`). Task files written
for this project are Apache-2.0.

Bugs were generated with the Python procedural modifiers of SWE-smith (`SWE-bench/SWE-smith@9b74ac08`, MIT),
used as a library; the generated patches are in [`candidates/`](candidates). Refactoring tasks, their hidden tests
and reference solutions were written by hand ([`hidden/`](hidden), [`solutions/`](solutions)). Instructions were
written by hand from the behaviour the failing tests check.

## Tasks

| Category | Count | What the agent gets |
|---|---|---|
| bug-fix | 7 | an issue-style description with expected behaviour; the failing tests are removed from its copy |
| test-repair | 7 | "the suite fails, fix the code"; failing tests are visible |
| multi-file | 6 | two or three bugs in different modules, described together |
| navigation | 6 | a user report with a reproduction and no file names |
| refactoring | 4 | a precise structural change; hidden tests check structure and behaviour |

The full list with fail-to-pass counts is in [`tasks.yaml`](tasks.yaml) and each `task.toml`.

## How a task is built

`python benchmarks/devbench/tools/make_task.py` rebuilds every task directory from `tasks.yaml`
deterministically. For each task it:

1. fetches the archive at the pinned commit (checksum verified), applies the bug patches, and for hidden-test
   tasks removes the fail-to-pass test functions from the agent's copy (a class whose tests are all hidden is
   removed whole; generated tests that have no definition stay visible and are counted as
   `fail_to_pass_visible` in `task.toml`);
2. writes `environment/Dockerfile`, which rebuilds the agent's view from the archive with dependencies from a
   pinned lock file (`locks/`), applies the patches, deletes them, and commits the result once as "Initial
   import", so there is no upstream history to diff against;
3. writes the verifier (`tests/`) and the reference solution (`solution/solve.sh`).

`tools/check_task.sh TASK_DIR` builds a task image and runs the verifier unchanged (must give 0) and after the
reference solution (must give 1), without Harbor.

## Verifier

`tests/verify.py` runs only at verification time. It deletes the repository's test directory and pytest
configuration files (`conftest.py`, `pytest.ini`, `.pytest.ini` at the root) and restores the pristine upstream
copy, adds the task's hidden tests, runs the whole suite offline, and gives reward 1 only if the suite exits 0,
every fail-to-pass test is reported as passed, and at least as many tests passed as in the reference run
(`min_passed`). Agent edits to tests therefore have no effect. Details go to `/logs/verifier/details.json`.

Known gaps: the verifier does not restore `pyproject.toml`, `setup.cfg` or `tox.ini`, so pytest options set
there by an agent would apply; it does not detect edits to installed third-party packages.

## Checks run

- Oracle 30/30 and nop 0/30 with `check_task.sh`; Harbor 0.27.0 oracle 10/10 and nop 0/10 on the first ten tasks.
- `tools/overlap.py`: no benchmark repository appears in the scale800 task names (22 repositories, from the
  Hugging Face file listing; no data downloaded), the SWE-smith Python profiles (133), SWE-bench (12),
  SWE-bench Pro (11) or the part of SWE-Gym that could be listed (7 of its repositories; the listing was rate
  limited). SWE-rebench, R2E-Gym and other large mined datasets were not checked.
- `agentlab audit` against the smoke tasks: no shared content, instructions or repositories.

## Limits

- All six libraries are popular and certainly in the base model's pretraining data; the bugs are synthetic, but
  the surrounding code is not new to the model. Nothing here measures contamination.
- SWE-smith procedural bugs are often local (one operator, one condition); several tasks proved easy for
  Qwen3.8-27B in the first runs. Difficulty labels have not been assigned.
- Six repositories and 30 tasks give wide confidence intervals; treat differences of a few tasks as noise.
