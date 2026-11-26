#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index 997a6d0..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -493,7 +493,7 @@ class peekable:
         if index < 0:
             self._cache.extend(self._it)
         elif index >= cache_len:
-            self._cache.extend(islice(self._it, index - cache_len))
+            self._cache.extend(islice(self._it, index + 1 - cache_len))
 
         return self._cache[index]
 
PATCH
