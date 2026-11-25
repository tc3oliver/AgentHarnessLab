import os, subprocess, tempfile

DOC = """# Project Title
Intro text.

## Install & Setup
```bash
# not a heading
## also not
```
### Step 1: Download!
#### too deep
## Usage ##
## Usage
## Usage
#Nospace
### Q&A (FAQ)
"""
WANT = """- [Project Title](#project-title)
  - [Install & Setup](#install--setup)
    - [Step 1: Download!](#step-1-download)
  - [Usage](#usage)
  - [Usage](#usage-1)
  - [Usage](#usage-2)
    - [Q&A (FAQ)](#qa-faq)
"""
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "t.md")
    with open(p, "w") as f:
        f.write(DOC)
    r = subprocess.run(["python3", "/app/gen_toc.py", p], capture_output=True, text=True, timeout=30, check=True)
    assert r.stdout == WANT, r.stdout
    with open(p, "w") as f:
        f.write("no headings here\n")
    r = subprocess.run(["python3", "/app/gen_toc.py", p], capture_output=True, text=True, timeout=30, check=True)
    assert r.stdout == ""
print("ok")
