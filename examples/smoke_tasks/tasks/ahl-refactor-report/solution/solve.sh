#!/bin/bash
set -e
cat > /app/report.py <<'AHL_EOF'
import sys


def parse_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    name, qty, price = line.split(",")
    return {"name": name.strip(), "qty": int(qty), "price": float(price)}


def summarize(records):
    lines = []
    total = 0.0
    for r in records:
        amount = r["qty"] * r["price"]
        total += amount
        lines.append((r["name"], amount))
    return {"lines": lines, "total": total}


def main(path):
    with open(path) as f:
        records = [r for r in map(parse_line, f) if r is not None]
    result = summarize(records)
    for name, amount in result["lines"]:
        print(f"{name}: {amount:.2f}")
    print(f"TOTAL: {result['total']:.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
AHL_EOF
