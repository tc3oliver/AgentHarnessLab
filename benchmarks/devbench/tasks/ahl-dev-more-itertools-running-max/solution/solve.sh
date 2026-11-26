#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/recipes.py b/more_itertools/recipes.py
index 9e33426..7c458d3 100644
--- a/more_itertools/recipes.py
+++ b/more_itertools/recipes.py
@@ -1520,7 +1520,7 @@ def _windowed_running_max(iterator, maxlen):
     s = deque()
 
     for index, value in enumerate(iterator):
-        if s[0][0] == index - maxlen and s:
+        if s and s[0][0] == index - maxlen:
             s.popleft()
         while s and value > s[-1][1]:
             s.pop()
PATCH
