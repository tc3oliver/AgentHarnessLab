#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index 7f435da..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -740,7 +740,10 @@ def strictly_n(iterable, n, too_short=None, too_long=None):
         )
 
     if too_long is None:
-        pass
+        too_long = lambda item_count: raise_(
+            ValueError,
+            f'Too many items in iterable (got at least {item_count})',
+        )
 
     it = iter(iterable)
 
PATCH
