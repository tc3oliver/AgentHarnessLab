#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/extensions/legacy_attrs.py b/markdown/extensions/legacy_attrs.py
index 2d27797..4b82c0e 100644
--- a/markdown/extensions/legacy_attrs.py
+++ b/markdown/extensions/legacy_attrs.py
@@ -47,10 +47,11 @@ class LegacyAttrs(Treeprocessor):
     def run(self, doc: etree.Element) -> None:
         """Find and set values of attributes ({@key=value}). """
         for el in doc.iter():
+            alt = el.get('alt', None)
             if alt is not None:
                 el.set('alt', self.handleAttributes(el, alt))
             if el.text and isString(el.text):
-                pass
+                el.text = self.handleAttributes(el, el.text)
             if el.tail and isString(el.tail):
                 el.tail = self.handleAttributes(el, el.tail)
 
PATCH
