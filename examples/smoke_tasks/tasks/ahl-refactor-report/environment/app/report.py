import sys


def main(path):
    total = 0.0
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, qty, price = line.split(",")
            rows.append((name.strip(), int(qty), float(price)))
    for name, qty, price in rows:
        amount = qty * price
        total += amount
        print(f"{name}: {amount:.2f}")
    print(f"TOTAL: {total:.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
