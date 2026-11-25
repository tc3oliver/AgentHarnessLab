#!/bin/bash
set -e
cat > /app/flatten.py <<'AHL_EOF'
import json
import sys


def flat(value, prefix, out):
    if isinstance(value, dict) and value:
        for k, v in value.items():
            flat(v, f"{prefix}.{k}" if prefix else k, out)
    elif isinstance(value, list) and value:
        for i, v in enumerate(value):
            flat(v, f"{prefix}.{i}" if prefix else str(i), out)
    elif prefix:
        out[prefix] = value


with open(sys.argv[1]) as f:
    doc = json.load(f)
out = {}
flat(doc, "", out)
with open(sys.argv[2], "w") as f:
    json.dump(out, f)
AHL_EOF
