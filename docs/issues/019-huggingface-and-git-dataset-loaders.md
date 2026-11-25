# 019: Hugging Face and git dataset loaders

Milestone: **v0.1**
Depends on: none

## Context

Only local datasets load today. Real datasets are pinned by 40-character revision ([../DATASETS.md](../DATASETS.md)); `core/config.py` already enforces the pin.

## Scope

Add loaders that fetch a Hugging Face or git dataset at the pinned revision into a local cache, verify the revision, compute the task-list hash, and respect licence flags (no redistribution of scale800). No credentials are read or logged.

## Acceptance criteria

- A pinned dataset loads and its task-list hash is stable across reloads.
- A wrong or moved revision fails loudly.
- Loaded datasets pass through the existing audit.
- Works offline from cache.

## Test method

Unit tests with a local git repository fixture; one real download of a small public dataset.
