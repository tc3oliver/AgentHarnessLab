#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/parser.py b/jmespath/parser.py
index e4e7616..cc8e804 100644
--- a/jmespath/parser.py
+++ b/jmespath/parser.py
@@ -112,6 +112,7 @@ class Parser(object):
             e.set_expression(expression)
             raise
         except exceptions.ParseError as e:
+            e.expression = expression
             raise
 
     def _parse(self, expression):
PATCH
