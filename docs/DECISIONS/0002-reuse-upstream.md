# 0002: Reuse Harbor, OpenEnv and TRL; pin one Harbor version

Status: accepted. Date: 2026-11-25.

## Context

Facts and versions: [UPSTREAM.md](../UPSTREAM.md). `openenv[harbor]==0.14.0` resolves to `harbor==0.25.0`; the latest Harbor is 0.27.0.

## Decision

Harbor runs tasks, sandboxes, agents and verifiers. OpenEnv captures tokens for training. TRL does GRPO. We write configuration, pinning, result mapping, comparison and reports. The `harbor` extra pins 0.25.0 so evaluation and training can share a version. SkyRL is the alternative if TRL on ROCm fails the v0.2 gate.

## Consequences

OpenCode v1 only for anything that trains (evaluation can use v2, see [0006](0006-harbor-subprocess.md)): 0.25.0 has no `opencode-v2` agent and OpenEnv has no seam for it. Our OpenCode numbers will not be comparable with the OpenCode 2.2.7 release results. Revisit when OpenEnv lifts its `harbor<0.26` cap. Trainer and inference server will use separate environments, so their dependency ranges do not have to agree.
