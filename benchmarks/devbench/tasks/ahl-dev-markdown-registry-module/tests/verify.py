"""Verifier for a devbench task. Runs only at verification time, from /tests, which the agent never sees.

1. Replace the repository's test directory and test configuration with the pristine upstream copy
   (restore.tar.gz), so edits to tests by the agent have no effect, and add the task's hidden tests.
2. Run the repository's test suite.
3. Reward 1 only if the suite exits 0, every fail-to-pass test is reported as passed, and at least as many
   tests passed as in the reference run (so a suite that silently collects less cannot pass).

Writes /logs/verifier/reward.txt and /logs/verifier/details.json. Needs no network.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

TESTS = Path("/tests")
APP = Path("/app")
LOGS = Path("/logs/verifier")


def restore(config: dict) -> None:
    for name in config["restore_paths"]:
        target = APP / name
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()
    with tarfile.open(TESTS / "restore.tar.gz") as archive:
        archive.extractall(APP, filter="data")
    hidden = TESTS / "hidden"
    if hidden.is_dir():
        shutil.copytree(hidden, APP, dirs_exist_ok=True)


def outcomes(runner: str, text: str) -> dict[str, str]:
    found = {}
    if runner == "unittest":
        for match in re.finditer(
            r"^(\S+) \(([\w.]+)\)(?:\n.*?)?\s\.\.\.\s"
            r"(ok|FAIL|ERROR|skipped.*|expected failure|unexpected success)$",
            text,
            re.M,
        ):
            found[f"{match.group(1)} ({match.group(2)})"] = match.group(3).split()[0].lower()
    else:
        for match in re.finditer(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)", text, re.M):
            found[match.group(2)] = match.group(1).lower()
    return found


def main() -> int:
    config = json.loads((TESTS / "config.json").read_text())
    LOGS.mkdir(parents=True, exist_ok=True)
    restore(config)
    env = dict(os.environ, PYTHONPATH=config["pythonpath"], PYTHONDONTWRITEBYTECODE="1")
    if config["runner"] == "unittest":
        cmd = [sys.executable, "-m", "unittest", "discover", "-v", config["tests_dir"]]
    else:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-rA",
            "--tb=short",
            *config["pytest_args"],
            config["tests_dir"],
        ]
    try:
        result = subprocess.run(
            cmd, cwd=APP, env=env, capture_output=True, text=True, timeout=config["timeout_s"]
        )
        text, code = result.stdout + "\n" + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        text, code = "timeout", -1
    (LOGS / "test_output.txt").write_text(text[-200_000:])
    seen = outcomes(config["runner"], text)
    passed = {name for name, status in seen.items() if status in ("passed", "ok")}
    missing = [name for name in config["fail_to_pass"] if name not in passed]
    ok = code == 0 and not missing and len(passed) >= config["min_passed"]
    details = {
        "exit_code": code,
        "passed": len(passed),
        "min_passed": config["min_passed"],
        "fail_to_pass_not_passed": missing,
        "reward": int(ok),
    }
    (LOGS / "details.json").write_text(json.dumps(details, indent=2))
    (LOGS / "reward.txt").write_text(f"{int(ok)}\n")
    print(json.dumps(details))
    return 0


if __name__ == "__main__":
    sys.exit(main())
