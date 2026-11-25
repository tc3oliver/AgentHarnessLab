#!/bin/bash
set -e
cat > /app/gen_toc.py <<'AHL_EOF'
import re
import sys

seen = {}
fence = False
with open(sys.argv[1]) as f:
    for line in f:
        line = line.rstrip("\n")
        if line.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r"^(#{1,3}) +(.*?)[ #]*$", line)
        if not m or not m.group(2):
            continue
        level, title = len(m.group(1)), m.group(2)
        anchor = re.sub(r"[^a-z0-9 \-]", "", title.lower()).replace(" ", "-")
        n = seen.get(anchor, 0)
        seen[anchor] = n + 1
        if n:
            anchor = f"{anchor}-{n}"
        print(f"{'  ' * (level - 1)}- [{title}](#{anchor})")
AHL_EOF
