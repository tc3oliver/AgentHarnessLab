#!/bin/bash
set -e
cd /app/repo
c=$(git log --format=%H --grep='^Tune timeout$' -n 1)
git revert --no-edit "$c"
