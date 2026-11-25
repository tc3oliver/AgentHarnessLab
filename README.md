# AgentHarnessLab

**Reproducible cross-harness agent post-training.** A research framework for evaluating, and later training, one model
under several unmodified agent harnesses. Model-, harness- and hardware-agnostic by design.

> **Pre-alpha.** Evaluations run through a *mock* runner or through Harbor. The Harbor path is verified with control
> agents and with real harnesses against a *scripted* endpoint. A real model has run only on the
> smoke tasks ([report](docs/reports/overnight-development.md)), and nothing trains.

## Status

| Capability | Status |
|---|---|
| Config validation, manifests, result schema, reports (JSONL, Parquet, Markdown) | Implemented, CPU-tested |
| Paired comparison with exact sign test, transfer gain and efficiency ratios | Implemented, CPU-tested |
| Local Harbor task loading, content hashing, leakage audit | Implemented, CPU-tested |
| 12 smoke tasks in Harbor format | Verified: oracle 12/12, nop 0/12 on Harbor 0.25.0 and 0.27.0, local Docker ([details](examples/smoke_tasks/README.md)) |
| Harbor runner | Verified: `agentlab eval` gives oracle 12/12 and nop 0/12 on Harbor 0.25.0 and 0.27.0 |
| Pi and OpenCode through Harbor | Wiring status in [COMPATIBILITY.md](docs/COMPATIBILITY.md); Pi and OpenCode v2 ran with a real model |
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

Control run on real Harbor (Docker, no model, no GPU; expect 12/12, then 0/12):

```bash
uv sync --extra harbor
uv run agentlab eval -c configs/experiments/smoke_oracle.yaml
uv run agentlab eval -c configs/experiments/smoke_nop.yaml
```

Pi and OpenCode against your own endpoint: [EVALUATION_GUIDE.md](docs/EVALUATION_GUIDE.md).

| Command | Does |
|---|---|
| `agentlab eval -c FILE` | run an evaluation with the mock or the Harbor runner |
| `agentlab compare BASE CANDIDATE` | compare two run directories, paired by task |
| `agentlab validate -c FILE` | check a config |
| `agentlab images -c FILE` | build task images with the harness preinstalled ([details](docs/HARNESS_IMAGES.md)) |
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
[Evaluation guide](docs/EVALUATION_GUIDE.md) · [Compatibility](docs/COMPATIBILITY.md) ·
[Upstream facts](docs/UPSTREAM.md) · [Decisions](docs/DECISIONS/README.md) · [Issue drafts](docs/issues/README.md)

## License

Code: [Apache-2.0](LICENSE). Models, datasets and other third-party material keep their own licences
([DATASETS.md](docs/DATASETS.md)); none are included in this repository.
