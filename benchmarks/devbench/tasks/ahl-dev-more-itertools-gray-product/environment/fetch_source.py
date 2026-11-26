"""Download a GitHub source archive at a pinned commit, check its sha256 and unpack it into the target directory."""

import hashlib
import io
import sys
import tarfile
import urllib.request

repo, commit, sha256, target = sys.argv[1:5]
data = urllib.request.urlopen(f"https://codeload.github.com/{repo}/tar.gz/{commit}", timeout=120).read()
found = hashlib.sha256(data).hexdigest()
if found != sha256:
    sys.exit(f"archive checksum mismatch: expected {sha256}, got {found}")
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    members = []
    for member in archive.getmembers():
        parts = member.name.split("/", 1)
        if len(parts) == 2 and parts[1]:
            member.name = parts[1]
            members.append(member)
    archive.extractall(target, members=members, filter="data")
