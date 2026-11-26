#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/lexer.py b/jmespath/lexer.py
index 55c860a..8db05e3 100644
--- a/jmespath/lexer.py
+++ b/jmespath/lexer.py
@@ -29,7 +29,7 @@ class Lexer(object):
             if self._current in self.SIMPLE_TOKENS:
                 yield {'type': self.SIMPLE_TOKENS[self._current],
                        'value': self._current,
-                       'start': self._position, 'end': self._position + 2}
+                       'start': self._position, 'end': self._position + 1}
                 self._next()
             elif self._current in self.START_IDENTIFIER:
                 start = self._position
@@ -50,7 +50,7 @@ class Lexer(object):
                 elif next_char == '?':
                     self._next()
                     yield {'type': 'filter', 'value': '[?',
-                           'start': start, 'end': start + 1}
+                           'start': start, 'end': start + 2}
                 else:
                     yield {'type': 'lbracket', 'value': '[',
                            'start': start, 'end': start + 1}
@@ -98,7 +98,7 @@ class Lexer(object):
                         # it back one location.
                         position = self._position
                     else:
-                        position = self._position - 2
+                        position = self._position - 1
                     raise LexerError(
                         lexer_position=position,
                         lexer_value='=',
PATCH
