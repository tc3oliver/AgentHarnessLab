#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/functions.py b/jmespath/functions.py
index f47d282..627b569 100644
--- a/jmespath/functions.py
+++ b/jmespath/functions.py
@@ -303,6 +303,8 @@ class Functions(metaclass=FunctionRegistry):
             return "object"
         elif isinstance(arg, (float, int)):
             return "number"
+        elif arg is None:
+            return "null"
 
     @signature({'types': ['array']}, {'types': ['expref']})
     def _func_sort_by(self, array, expref):
PATCH
