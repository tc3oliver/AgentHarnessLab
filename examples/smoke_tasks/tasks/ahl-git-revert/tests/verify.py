import subprocess

def git(*a):
    return subprocess.run(["git", "-C", "/app/repo", *a], capture_output=True, text=True, check=True).stdout

subjects = git("log", "--format=%s").splitlines()
assert len(subjects) == 5, subjects
assert subjects[1:] == ["Add log section", "Tune timeout", "Add feature flags", "Add base config"], subjects
assert subjects[0].startswith("Revert"), subjects[0]
assert "Tune timeout" in git("log", "-1", "--format=%B")
cfg = git("show", "HEAD:config.ini")
assert "timeout=30" in cfg.splitlines() and "timeout=0" not in cfg.splitlines(), cfg
assert "retries=3" in cfg.splitlines() and "[log]" in cfg and "level=info" in cfg, cfg
assert git("show", "HEAD:flags.txt") == "beta=on\n"
assert git("status", "--porcelain") == "", git("status", "--porcelain")
assert git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
assert open("/app/repo/config.ini").read() == cfg
print("ok")
