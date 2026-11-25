from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from types import TracebackType
from typing import TextIO

from pydantic import ValidationError

from agent_harness_lab.core.manifest import Manifest
from agent_harness_lab.core.results import TrialResult
from agent_harness_lab.errors import ConfigError, RunError
from agent_harness_lab.evaluation.compare import Comparison
from agent_harness_lab.evaluation.metrics import summarize

RESULTS_FILE = "results.jsonl"
SIMULATED = (
    "> **SIMULATED RESULTS.** No model, agent harness or verifier ran. "
    "These numbers test the pipeline and say nothing about any model."
)


class ResultWriter:
    """Appends and flushes one line per trial, so an interrupted run keeps what finished."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: TextIO | None = None

    def __enter__(self) -> ResultWriter:
        self._file = self._path.open("w", encoding="utf-8")
        return self

    def write(self, result: TrialResult) -> None:
        if self._file is None:
            raise RuntimeError("ResultWriter is not open")
        self._file.write(result.model_dump_json() + "\n")
        self._file.flush()

    def __exit__(
        self, kind: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        if self._file is not None:
            self._file.close()


def read_results(run_dir: Path) -> list[TrialResult]:
    path = run_dir / RESULTS_FILE
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        results = [TrialResult.model_validate_json(line) for line in lines if line]
    except OSError as exc:
        raise RunError(f"cannot read {path}: {exc.strerror}") from exc
    except ValidationError as exc:
        raise RunError(f"invalid record in {path}: {exc}") from exc
    if len({r.key for r in results}) != len(results):
        raise RunError(f"{path} contains duplicate trials")
    return results


def check_formats(formats: Sequence[str]) -> None:
    if "parquet" in formats:
        try:
            import_module("pyarrow.parquet")
        except ImportError as exc:
            raise ConfigError("parquet reports need: pip install 'agent-harness-lab[parquet]'") from exc


def write_reports(
    run_dir: Path, manifest: Manifest, results: Sequence[TrialResult], formats: Sequence[str]
) -> None:
    """JSONL is always written during the run; it is the source of truth for the other formats."""
    check_formats(formats)
    if "parquet" in formats:
        _write_parquet(run_dir / "results.parquet", results)
    if "markdown" in formats:
        (run_dir / "report.md").write_text(render_run(manifest, results), encoding="utf-8")


def _write_parquet(path: Path, results: Sequence[TrialResult]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    s, i, f = pa.string(), pa.int64(), pa.float64()
    schema = pa.schema(
        [
            ("schema_version", i),
            ("simulated", pa.bool_()),
            *((n, s) for n in ("dataset", "task_id", "task_hash", "harness", "harness_version")),
            ("attempt", i),
            ("seed", i),
            ("outcome", s),
            ("rewards", pa.map_(s, f)),
            *((n, i) for n in ("input_tokens", "output_tokens", "tool_calls", "model_calls")),
            ("latency_s", f),
            ("setup_s", f),
            ("image", s),
            ("cost_usd", f),
            ("error", s),
        ]
    )
    rows = [r.model_dump(mode="json") for r in results]
    for row in rows:
        row["rewards"] = None if row["rewards"] is None else list(row["rewards"].items())
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)


def _num(value: float | None, fmt: str = ".1f") -> str:
    return "n/a" if value is None else format(value, fmt)


def _table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    def line(cells: Sequence[object]) -> str:
        return "| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |"

    return [line(header), line(["---"] * len(header)), *(line(r) for r in rows)]


def render_run(manifest: Manifest, results: Sequence[TrialResult]) -> str:
    model = manifest.config.model
    adapter = f"{model.adapter.id}@{model.adapter.revision[:12]}" if model.adapter else "none"
    revision = model.revision[:12] if model.revision else "unpinned"
    commit = manifest.code.commit or "unknown"
    lines = [f"# Run: {manifest.name}", ""]
    if manifest.simulated:
        lines += [SIMULATED, ""]
    lines += [
        f"- Status: {manifest.status} ({manifest.n_recorded} of {manifest.n_planned} trials)",
        f"- Model: `{model.id}@{revision}`, adapter: `{adapter}`",
        f"- Seed: {manifest.seed}",
        f"- Code: `{commit}`" + (" (uncommitted changes)" if manifest.code.dirty else ""),
        f"- Config hash: `{manifest.config_hash}`",
        "",
        *_table(
            [
                "Dataset",
                "Harness",
                "Graded / trials",
                "Errors (infra / verifier / agent)",
                "pass@1",
                "Output tokens (mean)",
                "Tool calls (mean)",
                "Latency s (median)",
                "USD / solved",
            ],
            [
                [
                    s.dataset,
                    s.harness,
                    f"{s.n_graded} / {s.n_trials}",
                    f"{s.n_infra_errors} / {s.n_verifier_errors} / {s.n_agent_errors}",
                    _num(s.pass_at_1, ".1%"),
                    _num(s.mean_output_tokens, ".0f"),
                    _num(s.mean_tool_calls),
                    _num(s.median_latency_s),
                    _num(s.cost_per_solved_usd, ".4f"),
                ]
                for s in summarize(results)
            ],
        ),
        "",
        "Do not compare pass@1 across harnesses: they differ in context handling and budgets.",
        "`n/a` means at least one trial did not report the value.",
        "",
    ]
    return "\n".join(lines)


def render_comparison(c: Comparison) -> str:
    lines = [f"# Comparison: {c.base} -> {c.candidate}", ""]
    if c.simulated:
        lines += [SIMULATED, ""]
    if c.mismatches:
        lines += [f"> **NOT COMPARABLE AS-IS.** The runs differ in: {', '.join(c.mismatches)}.", ""]
    lines += [
        *_table(
            [
                "Dataset",
                "Harness",
                "Role",
                "Paired (dropped)",
                "Base pass@1",
                "Candidate pass@1",
                "Gain",
                "New / lost",
                "p (sign test)",
                "Tool-call ratio",
                "Output-token ratio",
                "Latency ratio",
            ],
            [
                [
                    x.dataset,
                    x.harness,
                    x.role,
                    f"{x.n_paired} ({x.n_dropped})",
                    _num(x.base_pass_at_1, ".1%"),
                    _num(x.candidate_pass_at_1, ".1%"),
                    _num(x.gain, "+.1%"),
                    f"{x.newly_solved} / {x.newly_lost}",
                    _num(x.sign_test_p, ".4f"),
                    _num(x.tool_call_ratio, ".2f"),
                    _num(x.output_token_ratio, ".2f"),
                    _num(x.latency_ratio, ".2f"),
                ]
                for x in c.cells
            ],
        ),
        "",
        "Ratios are candidate / base over tasks both solved. Gain in a `transfer` row is the transfer gain.",
        "p-values are per cell and not corrected for multiple comparisons.",
        "",
    ]
    return "\n".join(lines)
