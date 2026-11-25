import os, subprocess, sys, tempfile
sys.path.insert(0, "/app")
import report

assert report.parse_line("") is None
assert report.parse_line("   \n") is None
assert report.parse_line("# comment,1,2") is None
assert report.parse_line("  widget , 3,2.5\n") == {"name": "widget", "qty": 3, "price": 2.5}
s = report.summarize([{"name": "a", "qty": 2, "price": 1.25}, {"name": "b", "qty": 1, "price": 10.0}])
assert s["lines"] == [("a", 2.5), ("b", 10.0)] and abs(s["total"] - 12.5) < 1e-9, s
e = report.summarize([])
assert e["lines"] == [] and e["total"] == 0

for line, want in [("a,1,-2.5", {"name": "a", "qty": 1, "price": -2.5}),
                   ("	gear box,0,3", {"name": "gear box", "qty": 0, "price": 3.0}),
                   ("  #indented,1,1", None)]:
    got = report.parse_line(line)
    assert got == want, (line, got, want)
assert isinstance(report.parse_line("z,2,3")["qty"], int)
s2 = report.summarize([{"name": "x", "qty": 3, "price": 0.5}] * 3)
assert [n for n, _ in s2["lines"]] == ["x"] * 3 and abs(s2["total"] - 4.5) < 1e-9, s2

# main must go through the module's own parse_line and summarize (behavioural check using stubs)
import contextlib, io
seen = {}
def fake_parse(line):
    return {"name": "P", "qty": 1, "price": 1.0}
def fake_summarize(records):
    seen["records"] = list(records)
    return {"lines": [("S", 1.0)], "total": 9.0}
orig = (report.parse_line, report.summarize)
with tempfile.TemporaryDirectory() as d2:
    p2 = os.path.join(d2, "in.txt")
    with open(p2, "w") as f:
        f.write("one,1,1\ntwo,2,2\n")
    report.parse_line, report.summarize = fake_parse, fake_summarize
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            report.main(p2)
    finally:
        report.parse_line, report.summarize = orig
assert buf.getvalue() == "S: 1.00\nTOTAL: 9.00\n", buf.getvalue()
assert seen["records"] == [{"name": "P", "qty": 1, "price": 1.0}] * 2, seen

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "in.txt")
    with open(p, "w") as f:
        f.write("# header\nnut,10,0.15\n\n bolt , 4 , 2.25\n")
    r = subprocess.run(["python3", "/app/report.py", p], capture_output=True, text=True, timeout=30, check=True)
    assert r.stdout == "nut: 1.50\nbolt: 9.00\nTOTAL: 10.50\n", repr(r.stdout)
print("ok")
