#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/parser.py b/jmespath/parser.py
index 098ce27..cc8e804 100644
--- a/jmespath/parser.py
+++ b/jmespath/parser.py
@@ -445,6 +445,9 @@ class Parser(object):
             self._raise_parse_error_for_token(t, msg)
 
     def _error_nud_token(self, token):
+        if token['type'] == 'eof':
+            raise exceptions.IncompleteExpressionError(
+                token['start'], token['value'], token['type'])
         self._raise_parse_error_for_token(token, 'invalid token')
 
     def _error_led_token(self, token):
PATCH
