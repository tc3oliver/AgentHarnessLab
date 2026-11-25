# Evaluating Pi and OpenCode on a real endpoint

Status: the wiring is tested with a scripted endpoint (see [COMPATIBILITY.md](COMPATIBILITY.md)). **No real model has been
evaluated with this guide yet.**

## Before you start

1. **An endpoint you may use.** Never point an evaluation at a shared production server: agents issue many long requests
   and change its cache and latency. Use dedicated GPUs, and check that they are free first.
2. Harbor in the version the config names: `uv sync --extra harbor` for 0.25.0, or any other environment through
   `runner.command`.
3. Docker, and about 1 GB of downloads per trial unless the harness is baked into the task image.

## 1. Serve the model

Flags for `Qwen/Qwen3.8-27B` follow the reference adapter card; the ROCm build is **Unverified**
([HARDWARE.md](HARDWARE.md)). The server must listen on an address that containers can reach, and must require a key.

```bash
export VLLM_API_KEY="$AGENTLAB_API_KEY"   # not --api-key: arguments are visible in ps
vllm serve Qwen/Qwen3.8-27B --revision 37561816e66b5b9153b1b64c10968c18c1e6f4a0 \
  --host "$DOCKER_GATEWAY" --port 8000 \
  --language-model-only --max-model-len 131072 \
  --enable-prefix-caching --mamba-cache-mode align \
  --enable-auto-tool-choice --tool-call-parser qwen3_xml --reasoning-parser qwen3 \
  --default-chat-template-kwargs '{"enable_thinking": false}' \
  --override-generation-config '{"temperature": 0.8, "top_p": 1.0}'
```

`DOCKER_GATEWAY` is the host address seen from a container, usually 172.17.0.1. Set both `base_url` and `agent_base_url`
in the config to an address that works from the host and from the sandbox respectively.

For the reference adapter add `--enable-lora --max-lora-rank 32 --lora-modules pi-adapted=<path>` and set
`inference.served_model: pi-adapted`. Naming the base model with an adapter configured is rejected.

## 2. Check in this order

| Step | Command | Pass |
|---|---|---|
| 1 | `agentlab eval -c configs/experiments/smoke_oracle.yaml` | 12/12 |
| 2 | `agentlab eval -c configs/experiments/smoke_nop.yaml` | 0/12 |
| 3 | `uv run --extra harbor pytest -m docker` | all pass: real harnesses, scripted endpoint |
| 4 | `baseline.yaml` with one task and only Pi | one graded trial, tokens and tool calls not null |
| 5 | the same with only OpenCode | as above |
| 6 | `baseline.yaml` | 24 trials, at most 5% ungraded |
| 7 | step 6 again under another name | read the spread before trusting any difference |

In steps 4 and 5 also check the server log: model name, temperature, and that thinking is off.

## 3. Read the result

`report.md` shows pass@1 with error counts. Smoke results only show that the pipeline works; they are not a benchmark.
Raw traces are in `<run>/harbor/` and are ignored by git.
