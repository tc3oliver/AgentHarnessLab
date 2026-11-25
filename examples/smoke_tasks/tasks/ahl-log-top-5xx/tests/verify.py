import json, os, subprocess, tempfile

def line(ip, status, size="123", t="0.010", path="/x"):
    return f'{ip} - - [02/Mar/2024:11:00:00 +0000] "GET {path} HTTP/1.1" {status} {size} {t}'

lines = []
for ip, st in [("9.9.9.9", 500)] * 3 + [("1.1.1.1", 503)] * 3 + [("2.2.2.2", 502)] * 2 + \
        [("3.3.3.3", 599)] + [("1.1.1.1", 200)] * 4 + [("4.4.4.4", 404)] * 5 + [("5.5.5.5", 499)]:
    lines.append(line(ip, st))
lines += ["", "garbage here", '1.2.3.4 - - [bad] "GET / HTTP/1.1" 500', line("6.6.6.6", 500, size="-")]
lines.append(line("2.2.2.2", 500, size="0"))
text = "\n".join(lines) + "\n"
want_total = sum(1 for l in lines if l.startswith(("9.", "1.1", "2.2", "3.3", "4.4", "5.5", "6.6")))
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "t.log")
    with open(p, "w") as f:
        f.write(text)
    r = subprocess.run(["python3", "/app/loganalyze.py", p], capture_output=True, text=True, timeout=30, check=True)
    got = json.loads(r.stdout)
    assert got["total_requests"] == want_total, (got, want_total)
    assert got["top_5xx_ips"] == [["1.1.1.1", 3], ["2.2.2.2", 3], ["9.9.9.9", 3]], got
    open(p, "w").close()
    r = subprocess.run(["python3", "/app/loganalyze.py", p], capture_output=True, text=True, timeout=30, check=True)
    assert json.loads(r.stdout) == {"total_requests": 0, "top_5xx_ips": []}
print("ok")
