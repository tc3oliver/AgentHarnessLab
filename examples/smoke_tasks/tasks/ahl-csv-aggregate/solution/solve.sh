#!/bin/bash
set -e
cat > /app/aggregate.py <<'AHL_EOF'
import csv
import sys
from decimal import Decimal, InvalidOperation

totals = {}
with open(sys.argv[1], newline="") as f:
    for row in csv.DictReader(f):
        try:
            amt = Decimal((row.get("amount") or "").strip())
        except InvalidOperation:
            continue
        if not amt.is_finite():
            continue
        totals[row["region"]] = totals.get(row["region"], Decimal(0)) + amt
with open(sys.argv[2], "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["region", "total"])
    for r, t in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])):
        wr.writerow([r, f"{t:.2f}"])
AHL_EOF
