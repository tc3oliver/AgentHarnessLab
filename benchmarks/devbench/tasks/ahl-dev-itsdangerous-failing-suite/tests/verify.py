"""Verifier for a devbench task. Runs only at verification time, from /tests, which the agent never sees.

1. Replace the repository's test directory and root pytest files with the pristine upstream copy
   (restore.tar.gz), so edits to tests by the agent have no effect, and add the task's hidden tests.
2. Refuse files the agent added at the top of /app that would shadow the standard library or the test runner.
3. Run the suite isolated from agent-controlled configuration: `python -I` (no current directory on sys.path,
   no PYTHONPATH, no user site), pytest with the verifier's own ini file (`-c`), `--confcutdir` at the test
   directory (no conftest.py from elsewhere) and plugin autoloading disabled.
4. Reward 1 only if the suite exits 0, every fail-to-pass test passed, and at least as many tests passed as in
   the reference run (so a suite that silently collects less cannot pass).

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
SHADOW_EXTRA = {"pytest", "_pytest", "pluggy", "py", "conftest", "sitecustomize", "usercustomize"}


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


def shadowing_files() -> list[str]:
    """Top-level entries the agent created whose name is a standard-library or test-runner module."""
    out = subprocess.run(
        ["git", "-C", str(APP), "ls-files", "--others", "--directory", "--no-empty-directory"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    names = set(sys.stdlib_module_names) | SHADOW_EXTRA
    found = set()
    for entry in out.splitlines():
        top = entry.rstrip("/").split("/")[0]
        if top.removesuffix(".py").removesuffix(".pth") in names:
            found.add(top)
    return sorted(found)


def _norm(test_id: str) -> str:
    """jmespath numbers its compliance cases by directory-walk order, which differs between filesystems."""
    return re.sub(r"\[given\d+-", "[given-", test_id)


def pytest_result(text: str, fail_to_pass: list[str]) -> tuple[int, list[str]]:
    status: dict[str, list[str]] = {}
    for match in re.finditer(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)", text, re.M):
        status.setdefault(_norm(match.group(2)), []).append(match.group(1))
    passed = sum(s.count("PASSED") for s in status.values())
    missing = [t for t in fail_to_pass if set(status.get(_norm(t), [])) != {"PASSED"}]
    return passed, missing


def unittest_result(text: str, fail_to_pass: list[str]) -> tuple[int, list[str]]:
    """Counts come from the summary lines, so output printed in the middle of a test line does not matter."""
    ran = re.search(r"^Ran (\d+) tests? in", text, re.M)
    total = int(ran.group(1)) if ran else 0
    final = re.findall(r"^(?:OK|FAILED)(?: \((.*)\))?\s*$", text, re.M)
    counts = dict.fromkeys(("failures", "errors", "skipped", "expected failures", "unexpected successes"), 0)
    for part in (final[-1] if final else "").split(","):
        if "=" in part:
            key, value = part.strip().rsplit("=", 1)
            if key in counts:
                counts[key] = int(value)
    passed = total - sum(counts.values()) if final else 0
    bad = {m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR|UNEXPECTED SUCCESS): (\S+ \(\S+\))", text, re.M)}
    skipped = {m.group(1) for m in re.finditer(r"^(\S+ \([\w.]+\)).*?\.\.\. skipped", text, re.M)}
    missing = [
        t for t in fail_to_pass if t in bad or t in skipped or not re.search("^" + re.escape(t), text, re.M)
    ]
    return passed, missing


def main() -> int:
    config = json.loads((TESTS / "config.json").read_text())
    LOGS.mkdir(parents=True, exist_ok=True)
    restore(config)
    shadows = shadowing_files()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("PYTHONPATH", None)
    tests_dir = config["tests_dir"]
    if config["runner"] == "unittest":
        cmd = [sys.executable, "-I", "-m", "unittest", "discover", "-v", tests_dir]
    else:
        cmd = [
            sys.executable, "-I", "-m", "pytest",
            "-c", str(TESTS / "pytest.ini"), "--rootdir", str(APP), "--confcutdir", str(APP / tests_dir),
            "-p", "no:cacheprovider", "-rA", "--tb=short", tests_dir,
        ]  # fmt: skip
    try:
        result = subprocess.run(
            cmd, cwd=APP, env=env, capture_output=True, text=True, timeout=config["timeout_s"]
        )
        text, code = result.stdout + "\n" + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        text, code = "timeout", -1
    (LOGS / "test_output.txt").write_text(text[-200_000:])
    parse = unittest_result if config["runner"] == "unittest" else pytest_result
    passed, missing = parse(text, config["fail_to_pass"])
    ok = code == 0 and not missing and not shadows and passed >= config["min_passed"]
    details = {
        "exit_code": code,
        "passed": passed,
        "min_passed": config["min_passed"],
        "fail_to_pass_not_passed": missing,
        "shadowing_files": shadows,
        "reward": int(ok),
    }
    (LOGS / "details.json").write_text(json.dumps(details, indent=2))
    (LOGS / "reward.txt").write_text(f"{int(ok)}\n")
    print(json.dumps(details))
    return 0


if __name__ == "__main__":
    sys.exit(main())
