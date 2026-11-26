"""Build Harbor task directories for the development benchmark from tasks.yaml.

    python benchmarks/devbench/tools/make_task.py [TASK_ID ...]

For each task: fetch the upstream archive at the pinned commit (checksum verified), apply the bug patches,
optionally remove the fail-to-pass tests from the copy the agent sees, and write
  environment/  Dockerfile that rebuilds the agent's view from the pinned archive plus the patches
  tests/        verifier (restores pristine tests, adds hidden tests, runs the suite); not in the image
  solution/     reference solution for the oracle agent
The agent's image has no upstream git history: the repository is committed once as "Initial import".
"""

from __future__ import annotations

import ast
import gzip
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPOS = json.loads((ROOT / "repos.json").read_text())
CACHE = Path.home() / ".cache" / "agent-harness-lab" / "devbench-archives"
PYTEST_CONFIG = ("conftest.py", "pytest.ini", ".pytest.ini")


def archive(key: str) -> bytes:
    spec = REPOS["repositories"][key]
    path = CACHE / f"{key}-{spec['commit']}.tar.gz"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = f"https://codeload.github.com/{spec['github']}/tar.gz/{spec['commit']}"
        path.write_bytes(urllib.request.urlopen(url, timeout=120).read())
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec["archive_sha256"]:
        sys.exit(f"{key}: archive checksum mismatch")
    return data


def unpack(key: str, target: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive(key))) as tar:
        members = []
        for member in tar.getmembers():
            parts = member.name.split("/", 1)
            if len(parts) == 2 and parts[1]:
                member.name = parts[1]
                members.append(member)
        tar.extractall(target, members=members, filter="data")


def git(work: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=devbench", "-c", "user.email=devbench@example.invalid", *args],
        cwd=work,
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_location(test_id: str, runner: str, tests_dir: str) -> tuple[str, list[str]]:
    """File path and the class/function chain of a test id."""
    if runner == "unittest":
        match = re.fullmatch(r"(\S+) \(([\w.]+)\)", test_id)
        assert match, test_id
        dotted = match.group(2).split(".")
        return f"{tests_dir}/{'/'.join(dotted[:-2])}.py", dotted[-2:]
    path, *chain = test_id.split("::")
    return path, [re.sub(r"\[.*\]$", "", c) for c in chain]


def strip_tests(work: Path, test_ids: list[str], runner: str, tests_dir: str) -> list[str]:
    """Remove the given tests from their files. Returns ids without a definition (generated); they stay."""
    visible = []
    by_file: dict[str, set[tuple[str, ...]]] = {}
    for test_id in test_ids:
        path, chain = test_location(test_id, runner, tests_dir)
        by_file.setdefault(path, set()).add(tuple(chain))
    ids = {(p, tuple(c)): t for t in test_ids for p, c in [test_location(t, runner, tests_dir)]}
    for path, chains in by_file.items():
        file = work / path
        source = file.read_text()
        tree = ast.parse(source)
        drop: list[tuple[int, int]] = []

        found: set[tuple[str, ...]] = set()

        def visit(
            body: list[ast.stmt],
            prefix: tuple[str, ...],
            chains: set[tuple[str, ...]] = chains,
            drop: list[tuple[int, int]] = drop,
            found: set[tuple[str, ...]] = found,
        ) -> None:
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    here = (*prefix, node.name)
                    if here in chains:
                        start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
                        drop.append((start, node.end_lineno or node.lineno))
                        found.add(here)
                    elif isinstance(node, ast.ClassDef):
                        before = len(drop)
                        visit(node.body, here)
                        rest = [
                            n
                            for n in node.body
                            if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
                        ]
                        if rest and len(drop) - before == len(rest):  # every member hidden: drop the class
                            del drop[before:]
                            start = min([node.lineno, *(d.lineno for d in node.decorator_list)])
                            drop.append((start, node.end_lineno or node.lineno))

        visit(tree.body, ())
        visible += [ids[(path, c)] for c in sorted(chains - found)]
        lines = source.splitlines(keepends=True)
        for start, end in sorted(drop, reverse=True):
            del lines[start - 1 : end]
        new = "".join(lines)
        ast.parse(new)  # still valid Python
        file.write_text(new)
    return visible


def deterministic_tar(src: Path, names: list[str]) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        paths = set()
        for name in names:
            path = src / name
            if path.exists():
                paths.add(path)
            if path.is_dir():
                paths.update(p for p in path.rglob("*") if "__pycache__" not in p.parts)
        for path in sorted(paths):
            info = tar.gettarinfo(str(path), arcname=str(path.relative_to(src)))
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            if path.is_file():
                with path.open("rb") as handle:
                    tar.addfile(info, handle)
            else:
                tar.addfile(info)
    return buffer.getvalue()


def dockerfile(key: str) -> str:
    spec = REPOS["repositories"][key]
    return f"""FROM {REPOS["base_image"]}
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY fetch_source.py requirements.lock bug.patch hide.patch /tmp/build/
RUN python /tmp/build/fetch_source.py {spec["github"]} {spec["commit"]} {spec["archive_sha256"]} /app
WORKDIR /app
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0+devbench
RUN pip install --no-cache-dir --no-deps -r /tmp/build/requirements.lock \\
 && pip install --no-cache-dir --no-deps --no-build-isolation -e . \\
 && if [ -s /tmp/build/bug.patch ]; then git apply /tmp/build/bug.patch; fi \\
 && if [ -s /tmp/build/hide.patch ]; then git apply /tmp/build/hide.patch; fi \\
 && rm -rf /tmp/build && find /app -name __pycache__ -prune -exec rm -rf {{}} + \\
 && git init -q && git add -A \\
 && git -c user.name=dev -c user.email=dev@example.invalid commit -qm "Initial import" \\
 && git config --global --add safe.directory /app
"""


def build(task: dict) -> None:
    key = task["repo"]
    spec = REPOS["repositories"][key]
    runner = "unittest" if "unittest" in spec["test_cmd"] else "pytest"
    out = ROOT / "tasks" / task["id"]
    if out.exists():
        shutil.rmtree(out)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "src"
        unpack(key, work)
        pristine = Path(tmp) / "pristine"
        shutil.copytree(work, pristine, symlinks=True)
        git(work, "init", "-q")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "upstream")
        for name in task.get("bug_patches", []):
            git(work, "apply", str(ROOT / "candidates" / name))
        bug_patch = git(work, "diff")
        git(work, "commit", "-qam", "bug", "--allow-empty")
        visible = list(task["fail_to_pass"])
        if task.get("hide"):
            visible = strip_tests(work, task["fail_to_pass"], runner, spec["tests"])
        hide_patch = git(work, "diff")
        git(work, "commit", "-qam", "hide", "--allow-empty")
        if "solution_patch" in task:
            solution = (ROOT / "solutions" / task["solution_patch"]).read_text()
            git(work, "apply", "--check", "-", stdin=solution)
        else:
            solution = git(work, "diff", "HEAD~1", "HEAD~2", "--", ".", f":(exclude){spec['tests']}")
        restore_paths = [spec["tests"], *PYTEST_CONFIG]  # agent-created copies are deleted too
        restore = deterministic_tar(pristine, restore_paths)
        license_text = (pristine / spec["license_file"]).read_text()
        allowed = sorted(
            p.relative_to(pristine).as_posix()
            for d in (pristine, pristine / "src")
            if d.is_dir()
            for p in d.iterdir()
        )

    env = out / "environment"
    env.mkdir(parents=True)
    (env / "Dockerfile").write_text(dockerfile(key))
    shutil.copy(ROOT / "tools" / "fetch_source.py", env)
    shutil.copy(ROOT / "locks" / f"{key}.lock", env / "requirements.lock")
    (env / "bug.patch").write_text(bug_patch)
    (env / "hide.patch").write_text(hide_patch)

    tests = out / "tests"
    tests.mkdir()
    (tests / "restore.tar.gz").write_bytes(restore)
    shutil.copy(ROOT / "tools" / "verify.py", tests)
    hidden = ROOT / "hidden" / task["id"]
    if hidden.is_dir():
        shutil.copytree(hidden, tests / "hidden")
    config = {
        "runner": runner,
        "tests_dir": spec["tests"],
        "restore_paths": restore_paths,
        "fail_to_pass": task["fail_to_pass"],
        "min_passed": task.get("min_passed", spec.get("reference_passed", 0)),
        "timeout_s": 900,
    }
    (tests / "pytest.ini").write_text(spec["pytest_ini"])
    (tests / "allowed_names.json").write_text(json.dumps(allowed, indent=1) + "\n")
    (tests / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    (tests / "test.sh").write_text(
        "#!/bin/bash\nmkdir -p /logs/verifier\necho 0 > /logs/verifier/reward.txt\npython3 /tests/verify.py\n"
    )
    (tests / "test.sh").chmod(0o755)
    (tests / "UPSTREAM_LICENSE").write_text(license_text)

    sol = out / "solution"
    sol.mkdir()
    (sol / "solve.sh").write_text(
        f"#!/bin/bash\nset -euo pipefail\ncd /app\ngit apply <<'PATCH'\n{solution}PATCH\n"
    )
    (sol / "solve.sh").chmod(0o755)

    (out / "instruction.md").write_text(task["instruction"].strip() + "\n")
    meta = {
        "category": task["category"],
        "source": task["source"],
        "repository": spec["github"].lower(),
        "repository_commit": spec["commit"],
        "repository_license": spec["license"],
        "hidden_tests": bool(task.get("hide")) or hidden.is_dir(),
        "fail_to_pass": len(task["fail_to_pass"]),
        "fail_to_pass_visible": len(visible),
    }
    if task.get("difficulty"):
        meta["difficulty"] = task["difficulty"]
    if task.get("bug_patches"):
        meta["swe_smith_modifiers"] = sorted({n.split(".")[1] for n in task["bug_patches"]})
    toml = [
        'schema_version = "1.4"',
        "",
        "[task]",
        f'name = "ahl-devbench/{task["id"]}"',
        f'version = "{task.get("version", "1.0.0")}"',
        "authors = []",
        'keywords = ["devbench"]',
        "",
        "[metadata]",
    ]
    for k, v in meta.items():
        toml.append(f"{k} = {json.dumps(v)}")
    toml += [
        "",
        "[verifier]",
        "timeout_sec = 1200.0",
        "",
        "[agent]",
        "timeout_sec = 1800.0",
        "",
        "[environment]",
        "build_timeout_sec = 1200.0",
        "cpus = 2",
        "memory_mb = 4096",
        "gpus = 0",
        "",
    ]
    (out / "task.toml").write_text("\n".join(toml))
    print(f"built {task['id']}")


def main() -> None:
    tasks = yaml.safe_load((ROOT / "tasks.yaml").read_text())["tasks"]
    wanted = set(sys.argv[1:])
    for task in tasks:
        if not wanted or task["id"] in wanted:
            build(task)


if __name__ == "__main__":
    main()
