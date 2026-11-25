#!/bin/bash
set -e
cat > /app/durations.py <<'AHL_EOF'
import re

UNITS = {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0, "ms": 0.001}
PART = re.compile(r"\s*(\d+)\s*(ms|d|h|m|s)")


def parse_duration(text):
    pos = 0
    total = 0.0
    found = False
    while pos < len(text):
        m = PART.match(text, pos)
        if not m:
            if text[pos:].strip() == "" and found:
                break
            raise ValueError(f"bad duration: {text!r}")
        total += int(m.group(1)) * UNITS[m.group(2)]
        found = True
        pos = m.end()
    if not found:
        raise ValueError(f"bad duration: {text!r}")
    return total
AHL_EOF
