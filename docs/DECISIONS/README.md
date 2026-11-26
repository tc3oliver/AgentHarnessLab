# Architecture decision records

| ADR | Decision |
|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with entry-point plugins |
| [0002](0002-reuse-upstream.md) | Reuse Harbor, OpenEnv and TRL; pin one Harbor version |
| [0003](0003-unknown-is-not-zero.md) | Unknown values stay unknown; infrastructure errors are not failures |
| [0004](0004-task-harness-groups.md) | Advantage groups are Task x Harness |
| [0005](0005-explicit-not-implemented.md) | Planned features fail before any work, and simulated data is labelled |
| [0006](0006-harbor-subprocess.md) | Run Harbor as a subprocess |
| [0007](0007-development-benchmark.md) | A generated development benchmark instead of more smoke tasks |
| [0008](0008-default-attention-backend-for-evaluation.md) | Keep the default attention backend for evaluation until quality is compared (superseded by 0009) |
| [0009](0009-aiter-attention-backend.md) | Use `ROCM_AITER_UNIFIED_ATTN` for evaluation and rollouts |
| [0010](0010-unmodified-harnesses-for-rollouts.md) | Roll out with unmodified harnesses; bound hung commands with the trial budget |
