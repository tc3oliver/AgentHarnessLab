# 0010: Roll out with unmodified harnesses; bound hung commands with the trial budget

Status: accepted. Date: 2026-11-26.

## Context

devbench showed two harness behaviours that waste rollout time (COMPATIBILITY.md, "Harness behaviour seen on
devbench"):

- **Pi 1.5.2's bash tool has no default command timeout.** The model may pass one, but usually does not. In
  `devbench-r4-aiter`, five trials lost 786-1777 s each to commands that never returned.
- **OpenCode 2.2.7 offers native web tools.** Their approval prompt ends a non-interactive run with an error.

Harbor 0.27.0 has an option for the second (`disable_web_search`, enforced as an OpenCode policy) but none for the
first. A Pi command timeout would need a custom Pi extension that rewrites tool calls.

## Decision

- **OpenCode** runs with `disable_web_search: true` (`configs/harnesses/opencode-v2-noweb.yaml`) for evaluation and
  rollouts. This is a supported Harbor option, and the sandbox has no network anyway, so the tool could never
  have worked. Checked in `devbench/runs/noweb-check` (6 trials on the two tasks where the tool had ended runs):
  the model still called `websearch` twice, and both calls returned "Blocked by configuration policy". Every run
  continued, 6/6 were solved and there were 0 errors.
- **Pi** stays unmodified. The reference Pi adapter was trained with stock Pi, and harness-specific adaptation is
  what this project studies, so changing Pi's tools would change the object of study. Hung commands are bounded by
  the per-trial (evaluation) and per-rollout (training) wall-clock limits, which are set in every config.
- The hung-command rate is reported per run from the proxy join (trials whose harness time exceeds model time
  by more than 500 s).

## Consequences

- Some Pi rollouts end at the time limit with reward 0. That is a real property of stock Pi, and the RL
  signal may teach the model to pass timeouts or avoid such commands.
- Rollout batches wait for the slowest rollout, so the rollout time limit must be shorter than the evaluation
  budget. It is set in the training config, not here.
- If Pi adds a configurable default timeout, revisit this decision.
