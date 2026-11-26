"""Check the benchmark's upstream repositories against the repository lists in benchmarks/devbench/overlap.

    python benchmarks/devbench/tools/overlap.py

Exits 1 if a benchmark repository appears in any list. The lists and where they came from are described in
benchmarks/devbench/README.md; a repository missing from every list is not proof that no dataset uses it.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ours = {
        spec["github"].lower()
        for spec in json.loads((ROOT / "repos.json").read_text())["repositories"].values()
    }
    hits = 0
    for path in sorted((ROOT / "overlap").glob("*.txt")):
        listed = {line.strip().lower() for line in path.read_text().splitlines() if line.strip()}
        shared = sorted(ours & listed)
        hits += len(shared)
        print(f"{path.stem}: {len(listed)} repositories, shared: {shared or 'none'}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
