import json, os, subprocess, tempfile

CASES = [
    ({"a": {"b": 1}, "c": [10, {"d": 2}]}, {"a.b": 1, "c.0": 10, "c.1.d": 2}),
    ({"x": {}, "y": [], "z": None}, {"x": {}, "y": [], "z": None}),
    ({"deep": {"l1": {"l2": {"l3": "v"}}}, "t": True}, {"deep.l1.l2.l3": "v", "t": True}),
    ({"m": [[1, 2], [3]]}, {"m.0.0": 1, "m.0.1": 2, "m.1.0": 3}),
    ({"k.dot": {"n": 1.5}}, {"k.dot.n": 1.5}),
    ({}, {}),
]
with tempfile.TemporaryDirectory() as d:
    for i, (doc, want) in enumerate(CASES):
        a, b = os.path.join(d, f"i{i}.json"), os.path.join(d, f"o{i}.json")
        with open(a, "w") as f:
            json.dump(doc, f)
        subprocess.run(["python3", "/app/flatten.py", a, b], check=True, timeout=30)
        with open(b) as f:
            got = json.load(f)
        assert got == want, (doc, got, want)
print("ok")
