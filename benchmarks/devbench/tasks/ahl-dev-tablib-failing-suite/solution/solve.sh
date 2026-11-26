#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/core.py b/src/tablib/core.py
index 4717177..b0b56fd 100644
--- a/src/tablib/core.py
+++ b/src/tablib/core.py
@@ -259,7 +259,7 @@ class Dataset:
             if self.width:
                 is_valid = (
                     len(row) == self.width or
-                    len(row) == (self.width + len(self._dynamic_columns))
+                    len(row) == (self.width - len(self._dynamic_columns))
                 )
             else:
                 is_valid = True
PATCH
