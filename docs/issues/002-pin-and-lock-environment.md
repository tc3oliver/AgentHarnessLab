# 002: Pin and lock the serving and training environments

Milestone: **v0.1**
Depends on: none

## Context

`pyproject.toml` and `uv.lock` already pin the project itself. Harbor, OpenEnv, TRL, vLLM and PEFT conflict (see [../UPSTREAM.md](../UPSTREAM.md), Constraints 1-3), and a wrong Python can install the CUDA vLLM wheel.

## Scope

Add lock files and container recipes for the serving and evaluation stack (Harbor 0.25.0, OpenCode v1, Pi 1.6.0) and for training, with image digests recorded. Record resolver output. Add a check that prints `torch.version.hip` and versions for the manifest.

## Acceptance criteria

- A fresh install from the locks reproduces the same versions.
- The check fails loudly on a CUDA wheel in the ROCm environment.
- Image digests are recorded.
- Known-incompatible combinations are listed.

## Test method

Install in a clean container; run the check; diff versions against the locks.
