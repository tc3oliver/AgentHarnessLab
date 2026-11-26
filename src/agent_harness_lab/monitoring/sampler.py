"""Sample engine and GPU state every few seconds, and which container held which IP address.

Writes JSON lines: `{"kind": "engine", ...}` from the vLLM Prometheus endpoint (requests running and
waiting, KV-cache usage, token counters, preemptions), `{"kind": "gpu", ...}` from sysfs for one render node
(busy percent, VRAM bytes) and `{"kind": "container", ...}` when a container's address is first or last
seen, so that proxy log lines (client address) can be matched to Harbor trials. Reads no secrets.

Run: `python -m agent_harness_lab.monitoring.sampler --metrics http://127.0.0.1:8110/metrics
--render renderD184 --log samples.jsonl`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, TextIO

KEEP = re.compile(
    r"^vllm:(num_requests_(running|waiting)|kv_cache_usage_perc|gpu_cache_usage_perc|"
    r"(prompt|generation)_tokens_total|num_preemptions_total|prefix_cache_(queries|hits)_total)"
)
_LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+([-+0-9.eEinfNa]+)$")


def parse_metrics(text: str) -> dict[str, float]:
    """Sum each kept metric over its labels."""
    found: dict[str, float] = {}
    for line in text.splitlines():
        match = _LINE.match(line.strip())
        if match and KEEP.match(match.group(1)):
            name = match.group(1).removeprefix("vllm:")
            found[name] = found.get(name, 0.0) + float(match.group(3))
    return found


def gpu_state(render: str) -> dict[str, Any]:
    device = Path("/sys/class/drm") / render / "device"
    state: dict[str, Any] = {}
    for key, name in (("busy_percent", "gpu_busy_percent"), ("vram_used", "mem_info_vram_used")):
        try:
            state[key] = int((device / name).read_text().strip())
        except (OSError, ValueError):
            state[key] = None
    return state


def containers() -> dict[str, tuple[str, str]]:
    """Running container id -> (name, first IP address)."""
    docker = shutil.which("docker") or "docker"
    ps = subprocess.run([docker, "ps", "-q"], capture_output=True, text=True, check=False)  # noqa: S603
    ids = ps.stdout.split()
    if not ids:
        return {}
    out = subprocess.run(  # noqa: S603
        [
            docker,
            "inspect",
            "-f",
            "{{.Id}} {{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}",
            *ids,
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    found = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            found[parts[0]] = (parts[1].lstrip("/"), parts[2])
    return found


def _write(log: TextIO, record: dict[str, Any]) -> None:
    log.write(json.dumps(record) + "\n")
    log.flush()


def run(metrics: str, render: str | None, log_path: Path, interval: float) -> None:
    seen: dict[str, tuple[str, str]] = {}
    with log_path.open("a", encoding="utf-8") as log:
        while True:
            now = time.time()
            try:
                with urllib.request.urlopen(metrics, timeout=5) as response:  # noqa: S310 (operator-given URL)
                    _write(log, {"kind": "engine", "t": now, **parse_metrics(response.read().decode())})
            except OSError as exc:
                _write(log, {"kind": "engine", "t": now, "error": type(exc).__name__})
            if render:
                _write(log, {"kind": "gpu", "t": now, **gpu_state(render)})
            current = containers()
            for cid, (name, ip) in current.items():
                if cid not in seen:
                    _write(
                        log,
                        {"kind": "container", "t": now, "event": "seen", "id": cid, "name": name, "ip": ip},
                    )
            for cid, (name, ip) in seen.items():
                if cid not in current:
                    _write(
                        log,
                        {"kind": "container", "t": now, "event": "gone", "id": cid, "name": name, "ip": ip},
                    )
            seen = current
            time.sleep(max(0.0, interval - (time.time() - now)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--render", help="e.g. renderD184")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    run(args.metrics, args.render, args.log, args.interval)


if __name__ == "__main__":
    main()
