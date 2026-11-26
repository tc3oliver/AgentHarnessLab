#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index 3919445..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -1473,7 +1473,7 @@ def collapse(iterable, base_type=None, levels=None):
                     # Save our current location
                     stack.appendleft(node_group)
                     # Append the new child node
-                    stack.appendleft((level - 1, tree))
+                    stack.appendleft((level + 1, tree))
                     # Break to process child node
                     break
 
PATCH
