import os, subprocess, tempfile

def run(*files):
    return subprocess.run(["/app/merge_env.sh", *files], capture_output=True, text=True, timeout=30)

assert os.access("/app/merge_env.sh", os.X_OK)
with tempfile.TemporaryDirectory() as d:
    a, b, c = (os.path.join(d, n) for n in "abc")
    with open(a, "w") as f:
        f.write("# comment\nZED=1\n\nexport HOST=old.example\n  # indented comment\nNOEQUALS\nURL=http://x/?a=b&c=d\n")
    with open(b, "w") as f:
        f.write("HOST=new.example\n  PAD  =  spaced value \nQUOTED=\"hi there\"\nEMPTY=")
    with open(c, "w") as f:
        f.write("export ZED=3\nAAA=first\n")
    r = run(a, b, c)
    assert r.returncode == 0, r
    want = ("AAA=first\nEMPTY=\nHOST=new.example\nPAD=  spaced value \n"
            "QUOTED=\"hi there\"\nURL=http://x/?a=b&c=d\nZED=3\n")
    assert r.stdout == want, (r.stdout, want)
    r = run(a)
    assert r.stdout == "HOST=old.example\nURL=http://x/?a=b&c=d\nZED=1\n", r.stdout
    r = run(a, os.path.join(d, "nope"))
    assert r.returncode == 1 and r.stdout == "" and r.stderr.strip()
    assert run().stdout == ""
print("ok")
