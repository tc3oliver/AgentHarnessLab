# Contributing

```bash
uv sync --all-groups
uv run ruff format . && uv run ruff check . && uv run mypy && uv run pytest
```

- Core modules must be testable on CPU with mocks. Mark tests that need a GPU with `gpu` and tests that need Docker with
  `docker`; neither runs in default CI. GPU tests get their own manually
  triggered workflow together with the first GPU test; they must never run on pull requests.
- Do not merge a stub that looks finished. Raise `FeatureNotImplementedError` until the feature works and is tested.
- Check a third-party API in its source or official docs before using it, and record the version in `docs/UPSTREAM.md`.
- Describe capabilities as Verified, Planned or Unverified. "Verified" needs a command and its result.
- Never commit model weights, datasets, execution traces, credentials, or hidden tests and solutions of a benchmark.
- Do not train on smoke tasks, validation tasks or public benchmarks.
- Sign off commits (`git commit -s`). Contributions are licensed under Apache-2.0.

Architecture changes need an ADR in `docs/DECISIONS/`.
