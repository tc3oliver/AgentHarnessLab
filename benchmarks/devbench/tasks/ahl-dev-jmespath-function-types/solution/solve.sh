#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/functions.py b/jmespath/functions.py
index 48aa685..627b569 100644
--- a/jmespath/functions.py
+++ b/jmespath/functions.py
@@ -157,6 +157,9 @@ class Functions(metaclass=FunctionRegistry):
                     function_name, current[0], first, types)
             for element in current:
                 actual_typename = type(element).__name__
+                if actual_typename not in allowed:
+                    raise exceptions.JMESPathTypeError(
+                        function_name, element, actual_typename, types)
 
     @signature({'types': ['number']})
     def _func_abs(self, arg):
PATCH
