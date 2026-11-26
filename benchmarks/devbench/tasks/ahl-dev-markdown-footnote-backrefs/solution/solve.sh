#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/extensions/footnotes.py b/markdown/extensions/footnotes.py
index e735f39..580cf59 100644
--- a/markdown/extensions/footnotes.py
+++ b/markdown/extensions/footnotes.py
@@ -395,7 +395,7 @@ class FootnotePostTreeprocessor(Treeprocessor):
                 # Duplicate link the number of times we need to
                 # and point the to the appropriate references.
                 links = []
-                for index in range(2, duplicates + 0):
+                for index in range(2, duplicates + 1):
                     sib_link = copy.deepcopy(link)
                     sib_link.attrib['href'] = '%s%d%s%s' % (ref, index, self.footnotes.get_separator(), rest)
                     links.append(sib_link)
PATCH
