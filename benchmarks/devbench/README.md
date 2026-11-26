# devbench: a development coding benchmark

30 Harbor tasks (plus a 10-task hard tier, below) built from six permissively licensed Python repositories at pinned commits. They are for
**development decisions** in this project: comparing harnesses, adapters and serving settings. They are not
SWE-bench, not a held-out test set, and results on them must not be reported as either. Never train on them.

Dataset configs (split `validation`): [`devbench.yaml`](../../configs/datasets/devbench.yaml) is the original 30 tasks
(named explicitly and hash-pinned, so earlier results stay comparable);
[`devbench-hard.yaml`](../../configs/datasets/devbench-hard.yaml) is the hard tier.

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

## Hard tier

Ten tasks (`ahl-dev-hard-*`, `difficulty = "hard"` in `tasks.yaml` and `task.toml`) added because test-repair and
refactoring were solved in almost all trials, so they no longer separated harness or adapter conditions.

**Chosen by construction, not by model outcome.** No model was run on any candidate. The rules below were fixed
first, applied to the candidate pool (SWE-smith patches validated in the base images; `val` records), and the list
frozen. Only the oracle (must pass) and nop (must fail) checks may remove a task. Choosing patches that the base
model fails would bias later base-versus-adapter comparisons (regression to the mean).

Rules, applied in this order with ties broken by `sha256("devbench-hard:" + patch name)`:

1. Reuse: no patch of the first 30 tasks, and no function that any of their patches changes (checked on the
   changed lines against the source at the pinned commit, not only by patch id); not a non-source file
   (`test_tools.py`, `__meta__.py`, package `__init__.py`).
2. Failing-test record must be complete (the validator's failed list matches the failed count of the run; pytest
   subtest failures and truncated parametrised ids do not qualify), ids must not contain backslashes, and
   tests that cannot be hidden (jmespath `test_compliance.py`, generated) or that call a bundled sub-library
   directly (`test_tablib_dbfpy_packages_*`) are excluded, so every instruction can be written against a public
   entry point.
3. Repositories: no new repository; at most 2 tasks per repository; lark is not cleared and not used.
   itsdangerous has no qualifying candidate (its patches break hundreds of tests, or are already used).
4. 5 `bug-fix`: one patch with a single hunk, at most 2 fail-to-pass tests, modifier in `func_pm_remove_cond`,
   `func_pm_op_change_const`, `func_pm_remove_assign`, `func_pm_ctrl_shuffle` (edge-case behaviour). The
   instruction gives one concrete input, the wrong output and the expected behaviour.
5. 5 `multi-file`: three patches in three different source files of one repository, at most 8 failing tests per
   patch, failing-test sets of the three patches disjoint (each patch alone breaks at least one fail-to-pass
   test), no two patches in the same function; files are not reused between the two multi-file tasks of a
   repository. The instruction describes user-visible symptoms only. It may name the public API a user calls
   (for example `pysemver bump`, `Version.is_compatible`, `Dataset.export('rst', force_grid=True)`,
   `tablib.detect_format`), as a real issue would, but no internal module, file, private path or bundled
   sub-library. Bug-fix instructions follow the same naming rule.
6. All fail-to-pass tests are hidden from the agent's copy.

| Task | Repository | Category | Patches |
|---|---|---|---|
| `ahl-dev-hard-more-itertools-bucket-validator` | more-itertools | bug-fix | `more-itertools.func_pm_remove_cond.5b84c17dd3` |
| `ahl-dev-hard-more-itertools-strictly-n-default` | more-itertools | bug-fix | `more-itertools.func_pm_remove_assign.41120bd178` |
| `ahl-dev-hard-jmespath-parse-error-expression` | jmespath | bug-fix | `jmespath.func_pm_remove_assign.a2e847164e` |
| `ahl-dev-hard-jmespath-incomplete-expression` | jmespath | bug-fix | `jmespath.func_pm_remove_cond.1b95285fac` |
| `ahl-dev-hard-semver-deprecation-message` | semver | bug-fix | `semver.func_pm_remove_cond.27ee71ab70` |
| `ahl-dev-hard-markdown-setext-meta-registry` | markdown | multi-file | `markdown.func_pm_remove_cond.639b19fdb0`, `markdown.func_pm_class_rm_base.0efb045f29`, `markdown.func_pm_remove_wrapper.9cb95835f7` |
| `ahl-dev-hard-markdown-ancestors-html-smarty` | markdown | multi-file | `markdown.func_pm_remove_cond.b26af239b9`, `markdown.func_pm_op_change.dcea9a1a5b`, `markdown.func_pm_remove_cond.e563614f6f` |
| `ahl-dev-hard-tablib-dbf-yaml-rst` | tablib | multi-file | `tablib.func_pm_remove_assign.814393af23`, `tablib.func_pm_remove_assign.f4679dcec2`, `tablib.func_pm_op_change.86356b31d1` |
| `ahl-dev-hard-tablib-dbf-df-ods` | tablib | multi-file | `tablib.func_pm_class_rm_funcs.c04426e9de`, `tablib.func_pm_remove_assign.d8a31a7824`, `tablib.func_pm_ctrl_invert_if.72fd6fb804` |
| `ahl-dev-hard-semver-cli-compat-deprecated` | semver | multi-file | `semver.func_pm_remove_assign.cb027e125c`, `semver.func_pm_remove_cond.32aa744bb3`, `semver.func_pm_ctrl_invert_if.8812730f29` |

Known overlaps (not excluded by the rules, which look at functions, not test ids):

- The semver bug-fix and the semver multi-file task both patch the inner `wrapper` of `semver._deprecated.deprecated`
  (different lines, different tests); semver has too few qualifying candidates to avoid it.
- Some fail-to-pass tests are also fail-to-pass tests of one of the first 30 tasks, through different functions:
- `ahl-dev-hard-markdown-setext-meta-registry`: `testWikilinksMetaData (test_extensions.TestWikiLinks.testWikilinksMetaData)`
- `ahl-dev-hard-tablib-dbf-yaml-rst`: `tests/test_tablib.py::DBFTests::test_dbf_import_set`
- `ahl-dev-hard-tablib-dbf-df-ods`: `tests/test_tablib.py::DBFTests::test_dbf_export_set`, `tests/test_tablib.py::DBFTests::test_dbf_import_set`, `tests/test_tablib.py::ODSTests::test_ods_export_import_set`
- `ahl-dev-hard-semver-cli-compat-deprecated`: `tests/test_pysemver-cli.py::test_should_process_print`
- In `ahl-dev-hard-markdown-ancestors-html-smarty` the patch for the ancestor exclusion also removes the handling
  of a child's tail text. `test_ancestors_tail` passes with the ancestor check restored alone (checked), so the
  instruction describes only the ancestor symptom; the tail removal is not observable through the tests.

The same limits as for the first 30 apply (popular libraries, synthetic local bugs, six repositories);
`difficulty` is a label by construction, not a measured pass rate.

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
- Hard tier: oracle 10/10 and nop 0/10 with `check_task.sh`; rebuilding all 40 tasks twice leaves `git status` clean.
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
- The bug patch files are copied into the image build context and removed in a later `RUN`, so they stay readable
  in the image layers (all 40 tasks alike). The agent has no access to image layers from inside the container.
- Six repositories and 30 tasks give wide confidence intervals; treat differences of a few tasks as noise.
