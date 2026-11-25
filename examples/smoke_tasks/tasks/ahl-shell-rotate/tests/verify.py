import os, subprocess, tempfile

def run(d, keep):
    return subprocess.run(["/app/rotate.sh", d, str(keep)], capture_output=True, text=True, timeout=30)

def populate(d, names):
    for n in names:
        if n.endswith("/"):
            os.makedirs(os.path.join(d, n))
        else:
            with open(os.path.join(d, n), "w") as f:
                f.write("x")

assert os.access("/app/rotate.sh", os.X_OK), "rotate.sh must be executable"
logs = ["app-2024-01-0%d.log" % i for i in range(1, 8)]
other = ["notes.txt", "app-2024-01-09.log.gz", "sub/"]
with tempfile.TemporaryDirectory() as d:
    populate(d, logs + other)
    with open(os.path.join(d, "sub", "app-2099.log"), "w") as f:
        f.write("x")
    r = run(d, 3)
    assert r.returncode == 0 and r.stdout == "", (r.returncode, r.stdout)
    left = sorted(os.listdir(d))
    assert left == sorted(["app-2024-01-07.log", "app-2024-01-06.log", "app-2024-01-05.log"] + [o.rstrip("/") for o in other]), left
    assert os.path.exists(os.path.join(d, "sub", "app-2099.log"))
with tempfile.TemporaryDirectory() as d:
    populate(d, ["a b 2.log", "a b 1.log", "keep.txt"])
    assert run(d, 5).returncode == 0
    assert sorted(os.listdir(d)) == ["a b 1.log", "a b 2.log", "keep.txt"]
    assert run(d, 1).returncode == 0
    assert sorted(os.listdir(d)) == ["a b 2.log", "keep.txt"]
    assert run(d, 0).returncode == 0
    assert sorted(os.listdir(d)) == ["keep.txt"]
r = run("/nonexistent-dir-xyz", 1)
assert r.returncode == 2 and r.stderr.strip(), (r.returncode, r.stderr)
print("ok")
