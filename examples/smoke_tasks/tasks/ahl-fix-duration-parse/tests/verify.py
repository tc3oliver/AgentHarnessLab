import sys
sys.path.insert(0, "/app")
from durations import parse_duration as p

def close(a, b):
    return abs(a - b) < 1e-9

for text, want in [("1h30m", 5400), ("2d", 172800), ("1h 30m 5s", 5405), ("250ms", 0.25), ("90s", 90),
                   ("1m30s", 90), ("30s1h", 3630),
                   ("5m5ms", 300.005), ("1d1h1m1s1ms", 90061.001), ("0s", 0), (" 3s ", 3), ("1m 1ms", 60.001)]:
    got = p(text)
    assert isinstance(got, float), (text, type(got))
    assert close(got, want), (text, got, want)
for bad in ["", "   ", "abc", "5", "5x", "1h junk", "h", "1h30", "1.5h", "-1s", "1h-30m"]:
    try:
        p(bad)
    except ValueError:
        continue
    raise AssertionError(f"{bad!r} should raise ValueError")
print("ok")
