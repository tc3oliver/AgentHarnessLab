# AgentHarnessLab

**Reproducible cross-harness agent post-training.** A research framework for evaluating, and later training, one model
under several unmodified agent harnesses. Model-, harness- and hardware-agnostic by design.

> **Pre-alpha.** Today the framework around an evaluation works, on CPU, with a *mock* runner.
> It does not yet run a real agent, serve a model or train anything.

## Status

| Capability | Status |
|---|---|
| Config validation, manifests, result schema, reports (JSONL, Parquet, Markdown) | Implemented, CPU-tested |
| Paired comparison with exact sign test, transfer gain and efficiency ratios | Implemented, CPU-tested |
| Local Harbor task loading, content hashing, leakage audit | Implemented, CPU-tested |
| 12 smoke tasks in Harbor format | Verified: oracle 12/12, nop 0/12 on Harbor 0.25.0 and 0.27.0, local Docker ([details](examples/smoke_tasks/README.md)) |
| Pi and OpenCode evaluation through Harbor | Planned, v0.1 |
| Single-harness RL (TRL AsyncGRPO + LoRA) | Planned, v0.2 |
| Joint multi-harness RL | Planned, v0.3 |
| Adapter merging and the full research comparison | Planned, v0.4 |
| Large MoE models | Planned, v0.5 |
| AMD MI325X / ROCm training | Unverified |

## Quick start (no GPU, no Docker, no model)

Needs [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
git clone https://github.com/tc3oliver/AgentHarnessLab && cd AgentHarnessLab
uv sync
uv run agentlab eval -c configs/experiments/mock_base.yaml
uv run agentlab eval -c configs/experiments/mock_joint.yaml
uv run agentlab compare runs/base runs/joint
```

Each run directory holds `manifest.json`, `results.jsonl` and `report.md`. The numbers are invented from the seed and
every report says so. Add `--overwrite` to run an experiment again.

| Command | Does |
|---|---|
| `agentlab eval -c FILE` | run an evaluation (mock runner only; `baseline.yaml` exits with code 3) |
| `agentlab compare BASE CANDIDATE` | compare two run directories, paired by task |
| `agentlab validate -c FILE` | check a config |
| `agentlab audit --train D.yaml --eval D.yaml` | look for train/evaluation leakage in local datasets |
| `agentlab train -c FILE` | validate a training config, then exit with code 3: not implemented |

## Research questions

1. Can one LoRA adapter improve Pi and OpenCode at the same time?
2. Does joint multi-harness RL beat per-harness training followed by adapter merging?
3. Can tool calls, tokens, latency and cost per solved task go down?
4. Do the methods carry over to other model generations?

Transfer, merging and small-scale joint RL have been reported before; see [RESEARCH.md](docs/RESEARCH.md) for what is new here.

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Research](docs/RESEARCH.md) · [Datasets](docs/DATASETS.md) ·
[Experiments](docs/EXPERIMENTS.md) · [Hardware](docs/HARDWARE.md) · [Roadmap](docs/ROADMAP.md) ·
[Upstream facts](docs/UPSTREAM.md) · [Decisions](docs/DECISIONS/README.md) · [Issue drafts](docs/issues/README.md)

## License

Code: [Apache-2.0](LICENSE). Models, datasets and other third-party material keep their own licences
([DATASETS.md](docs/DATASETS.md)); none are included in this repository.
