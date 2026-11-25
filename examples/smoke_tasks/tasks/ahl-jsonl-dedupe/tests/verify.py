import os, subprocess, tempfile

IN = """{"id": 1, "v": "a"}
{"id": "1", "v": "str"}
{"id": true, "v": "t"}
{"id": 1.0, "v": "f"}

not json
{"id": 2, "v": "b"}
[1, 2]
{"v": "noid"}
{"id": 1, "v": "a2", "extra": true}
{"id": 2, "v": "b2"}
{"id": null, "v": "n"}
{"id": null, "v": "n2"}
{"v": 1, "id": 3}"""
WANT = """{"extra": true, "id": 1, "v": "a2"}
{"id": "1", "v": "str"}
{"id": true, "v": "t"}
{"id": 1.0, "v": "f"}
{"id": 2, "v": "b2"}
{"id": null, "v": "n2"}
{"id": 3, "v": 1}
"""
with tempfile.TemporaryDirectory() as d:
    a, b = os.path.join(d, "i.jsonl"), os.path.join(d, "o.jsonl")
    with open(a, "w") as f:
        f.write(IN)
    subprocess.run(["python3", "/app/dedupe.py", a, b], check=True, timeout=30)
    got = open(b).read()
    assert got == WANT, got
print("ok")
