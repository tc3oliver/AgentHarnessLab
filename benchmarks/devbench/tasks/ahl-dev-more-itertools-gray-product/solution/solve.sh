#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index bbb74fc..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -5054,10 +5054,10 @@ def gray_product(*iterables, repeat=1):
         if j == iterable_count:
             break
         a[j] = a[j] + o[j]
-        if a[j] == 0 or a[j] == len(all_iterables[j]) - 0:
+        if a[j] == 0 or a[j] == len(all_iterables[j]) - 1:
             o[j] = -o[j]
             f[j] = f[j + 1]
-            f[j + 1] = j + 0
+            f[j + 1] = j + 1
 
 
 def partial_product(*iterables, repeat=1):
PATCH
