#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/blockprocessors.py b/markdown/blockprocessors.py
index 2e2111d..11ff0dd 100644
--- a/markdown/blockprocessors.py
+++ b/markdown/blockprocessors.py
@@ -519,6 +519,9 @@ class SetextHeaderProcessor(BlockProcessor):
             level = 2
         h = etree.SubElement(parent, 'h%d' % level)
         h.text = lines[0].strip()
+        if len(lines) > 2:
+            # Block contains additional lines. Add to  master blocks for later.
+            blocks.insert(0, lines[2])
 
 
 class HRProcessor(BlockProcessor):
diff --git a/markdown/extensions/meta.py b/markdown/extensions/meta.py
index 7379139..bc47354 100644
--- a/markdown/extensions/meta.py
+++ b/markdown/extensions/meta.py
@@ -56,7 +56,7 @@ class MetaExtension (Extension):
         self.md.Meta = {}
 
 
-class MetaPreprocessor():
+class MetaPreprocessor(Preprocessor):
     """ Get Meta-Data. """
 
     def run(self, lines: list[str]) -> list[str]:
diff --git a/markdown/util.py b/markdown/util.py
index 4a83db2..29ffa24 100644
--- a/markdown/util.py
+++ b/markdown/util.py
@@ -391,6 +391,13 @@ class Registry(Generic[_T]):
 
         Set `strict=False` to fail silently. Otherwise a [`ValueError`][] is raised for an unknown `name`.
         """
+        try:
+            index = self.get_index_for_name(name)
+            del self._priority[index]
+            del self._data[name]
+        except ValueError:
+            if strict:
+                raise
 
     def _sort(self) -> None:
         """
PATCH
