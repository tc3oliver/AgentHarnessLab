#!/bin/bash
set -e
cat > /app/stats.py <<'AHL_EOF'
def mean(values):
    return sum(values) / len(values)


def median(values):
    if not values:
        raise ValueError("median of empty list")
    s = sorted(values)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2
AHL_EOF
