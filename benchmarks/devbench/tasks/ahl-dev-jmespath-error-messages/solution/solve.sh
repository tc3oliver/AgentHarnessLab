#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/lexer.py b/jmespath/lexer.py
index ea52a2b..8db05e3 100644
--- a/jmespath/lexer.py
+++ b/jmespath/lexer.py
@@ -148,7 +148,7 @@ class Lexer(object):
                 # We're at the EOF.
                 raise LexerError(lexer_position=start,
                                  lexer_value=self._expression[start:],
-                                 message=delimiter % "Unclosed %s delimiter")
+                                 message="Unclosed %s delimiter" % delimiter)
             buff += self._current
             self._next()
         # Skip the closing delimiter.
diff --git a/jmespath/parser.py b/jmespath/parser.py
index ef8207a..cc8e804 100644
--- a/jmespath/parser.py
+++ b/jmespath/parser.py
@@ -289,7 +289,7 @@ class Parser(object):
             prev_t = self._lookahead_token(-2)
             raise exceptions.ParseError(
                 prev_t['start'], prev_t['value'], prev_t['type'],
-                prev_t['value'] % "Invalid function name '%s'")
+                "Invalid function name '%s'" % prev_t['value'])
         name = left['value']
         args = []
         while not self._current_token() == 'rparen':
PATCH
