#!/bin/bash
set -e
cat > /app/loganalyze.py <<'AHL_EOF'
import json
import re
import sys
from collections import Counter

LINE = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "\S+ \S+ [^"]*" (\d{3}) (\d+|-) \S+$')

total = 0
errs = Counter()
with open(sys.argv[1], errors="replace") as f:
    for line in f:
        m = LINE.match(line.rstrip("\n"))
        if not m:
            continue
        total += 1
        if m.group(2).startswith("5"):
            errs[m.group(1)] += 1
top = sorted(errs.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
print(json.dumps({"total_requests": total, "top_5xx_ips": [list(t) for t in top]}))
AHL_EOF
