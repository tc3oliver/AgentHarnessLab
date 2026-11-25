#!/bin/bash
set -e
cat > /app/dedupe.py <<'AHL_EOF'
import json
import sys

order = []
last = {}
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict) or "id" not in rec:
            continue
        key = json.dumps(rec["id"], sort_keys=True)
        if key not in last:
            order.append(key)
        last[key] = rec
with open(sys.argv[2], "w") as f:
    for key in order:
        f.write(json.dumps(last[key], sort_keys=True) + "\n")
AHL_EOF
