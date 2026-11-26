#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index 56b81a0..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -1243,6 +1243,8 @@ class bucket:
     def __iter__(self):
         for item in self._it:
             item_value = self._key(item)
+            if self._validator(item_value):
+                self._cache[item_value].append(item)
 
         return iter(self._cache)
 
PATCH
