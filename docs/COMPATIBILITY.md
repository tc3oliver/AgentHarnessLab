# Compatibility

Checked 2026-11-25. **Run** = executed by us; **read** = read in source or metadata; **-** = not available.
No cell says anything about model quality, and nothing here ran on a GPU.

## Evaluation: harness x Harbor

A "scripted run" is the real, unmodified harness in a Docker sandbox, driven by a scripted OpenAI-compatible server for one
tool call on one smoke task. It checks installation, endpoint wiring, the tool loop, token accounting and grading.

| Agent | Harbor 0.25.0 (default) | Harbor 0.27.0 |
|---|---|---|
| `oracle`, `nop` (12 smoke tasks through `agentlab eval`) | Run: 12/12, 0/12 | Run: 12/12, 0/12 |
| `pi` 1.6.0 | Run: scripted, solved | read |
| `pi` 1.5.2 (reference release) | read | Run: scripted, solved |
| `opencode` 1.19.6 (v1) | Run: scripted, solved, exits 1 (below) | Run: scripted, solved, exits 1 |
| `opencode` 1.18.30 (v1, OpenEnv's qualification pin) | Run: scripted, solved, exits 0 (default pin) | read |
| `opencode-v2` 2.2.7 (reference release) | - (no such agent) | Run: scripted, solved |
| Any agent on a real model | **not run** | **not run** |

`SUPPORTED_HARBOR` and each adapter's `harbor_versions` encode the Harbor versions; others are rejected at preflight. Any exact
harness version is accepted, so check this table before changing a pin.

## Training stack

| Component | Constraint (read) |
|---|---|
| `openenv[harbor]` 0.14.0 | resolves `harbor` 0.25.0; OpenEnv main caps `harbor<0.26` |
| OpenEnv seams | `pi` and `opencode` validated upstream; no `opencode-v2` seam |
| TRL `examples/async_grpo_harbor` | pins OpenEnv 0.7.0 |
| TRL 1.18.2 | `vllm>=0.23,<0.34` |

So OpenCode v2 can be **evaluated** today and **trained** only after OpenEnv gains a seam and lifts its cap.

## Matching the reference evaluation

The reference release used Pi 1.5.2, OpenCode 2.2.7, 100 agent steps, 131,072 context tokens, temperature 0.8, top-p 1.0,
thinking off, and ran its trials through OpenEnv in remote sandboxes.

| Item | Here |
|---|---|
| Harness versions | `configs/harnesses/pi-reference.yaml`, `opencode-v2.yaml`, both with Harbor 0.27.0 |
| 100 steps | Pi: `max_turns: 100`. OpenCode: Harbor has no step limit; the reference capped it in OpenEnv's proxy. **Gap** |
| Sampling, thinking | server flags ([EVALUATION_GUIDE.md](EVALUATION_GUIDE.md)); not checked by us |
| Output limit per call | Pi requested 16,384 and OpenCode 32,000 tokens in our runs; the reference card reports a 32k cap. **Gap for Pi** |
| Context window | Harbor 0.27.0 has a Pi `context_window` option we do not set; compaction may differ. **Gap** |
| Tools | OpenEnv disables OpenCode v1's `task`, `question`, `webfetch` in training; the plain agent has them (v2 also `websearch`). **Gap** |
| Harbor version of the reference | unknown to us |

Until the gaps are closed, our numbers must be labelled "not protocol-matched".

## Known problems

- **OpenCode 1.19.6 exits with status 1** after a normal finish (`EPIPE: broken pipe`, through Harbor's output pipe).
  Harbor raises `NonZeroAgentExitCodeError`, or another type when the output happens to contain a phrase such as "rate
  limit". If OpenCode itself recorded a normal stop we treat both alike: the verifier decides, so pass@1 is unaffected, but
  a wrong solution is reported as `agent_error` instead of `failed`.
- **Reported versions.** For Pi and OpenCode v1 Harbor repeats the requested version, so the drift check can only fire for
  other agents. Versions must be full `x.y.z`, which npm installs exactly. Harbor checks OpenCode v2's binary itself.
- **Model name prefix.** Pi needs `openai/`: Harbor only strips providers that LiteLLM knows, and would otherwise send
  `agentlab/<model>` to the server. OpenCode must not use `openai/`, which selects the Responses API.
- **Install time.** Agents are installed into every sandbox. OpenCode needs `apt` and `npm`; on our network that took more
  than Harbor's 360 s limit, hence `setup_timeout_s: 1800`. [Prebuilt images](HARNESS_IMAGES.md) remove this cost.
- **Token accounting.** OpenCode sends a session-title request that Harbor does not count. Subagent calls are missing from
  ATIF, so tool and model call counts become null when a subagent ran. Whether output tokens include reasoning tokens for
  every harness is **unverified**.
- **Harbor 0.25.0** keeps `oracle` script failures silent (`failed`), while 0.27.0 reports `agent_error`.
