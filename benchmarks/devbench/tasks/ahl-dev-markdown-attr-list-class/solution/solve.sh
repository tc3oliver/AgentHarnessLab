#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/extensions/attr_list.py b/markdown/extensions/attr_list.py
index 48dce77..060e476 100644
--- a/markdown/extensions/attr_list.py
+++ b/markdown/extensions/attr_list.py
@@ -195,9 +195,9 @@ class AttrListTreeprocessor(Treeprocessor):
                 # add to class
                 cls = elem.get('class')
                 if cls:
-                    elem.set('class', v)
-                else:
                     elem.set('class', '{} {}'.format(cls, v))
+                else:
+                    elem.set('class', v)
             elif v is None:
                 # assign a valueless attribute. Maintain the historic
                 # `key="key"` representation only for known boolean
PATCH
