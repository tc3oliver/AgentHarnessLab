"""Verifier for a devbench task. Runs only at verification time, from /tests, which the agent never sees.

1. Replace the repository's test directory and root pytest files with the pristine upstream copy
   (restore.tar.gz), so edits to tests by the agent have no effect, and add the task's hidden tests.
2. Refuse files the agent added under /app that would run inside the test process (sitecustomize, modules
   shadowing the standard library or the test runner on sys.path).
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
    """Files under /app that would run code inside the test process, unless they were in the pristine image.

    Every directory under /app on the interpreter's own sys.path (the editable install adds /app or /app/src)
    is checked for modules named like the standard library or the test runner, and the whole tree for
    sitecustomize/usercustomize. Git is not consulted: an agent can commit files or delete .git.
    """
    allowed = set(json.loads((TESTS / "allowed_names.json").read_text()))
    probe = subprocess.run(
        [sys.executable, "-I", "-c", "import json, sys; print(json.dumps(sys.path))"],
        capture_output=True,
        text=True,
        check=True,
    )
    names = set(sys.stdlib_module_names) | SHADOW_EXTRA
    found = set()
    for entry in json.loads(probe.stdout):
        path = Path(entry or ".").resolve()
        if path != APP and APP not in path.parents:
            continue
        for child in path.iterdir() if path.is_dir() else []:
            rel = child.relative_to(APP).as_posix()
            if child.name.removesuffix(".py") in names and rel not in allowed:
                found.add(rel)
    for pattern in ("sitecustomize.py", "usercustomize.py", "sitecustomize", "usercustomize"):
        for child in APP.rglob(pattern):
            rel = child.relative_to(APP).as_posix()
            if ".git" not in child.parts and rel not in allowed:
                found.add(rel)
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
        text, code, stderr = result.stdout + "\n" + result.stderr, result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        text, code, stderr = "timeout", -1, ""
    (LOGS / "test_output.txt").write_text(text[-200_000:])
    if config["runner"] == "unittest":  # unittest reports on stderr; tests can print anything to stdout
        passed, missing = unittest_result(stderr, config["fail_to_pass"])
    else:
        passed, missing = pytest_result(text, config["fail_to_pass"])
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
