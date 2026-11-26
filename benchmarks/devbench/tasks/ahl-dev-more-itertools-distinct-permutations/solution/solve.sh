#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index 28c781f..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -904,12 +904,12 @@ def distinct_permutations(iterable, r=None):
 
     if 0 < r <= size:
         if sortable:
+            return algorithm(items)
+        else:
             return (
                 permuted_items(permuted_indices)
                 for permuted_indices in algorithm(indices)
             )
-        else:
-            return algorithm(items)
 
     return iter(() if r else ((),))
 
PATCH
