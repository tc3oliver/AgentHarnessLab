#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/extensions/md_in_html.py b/markdown/extensions/md_in_html.py
index 2f109d4..1a4ec0e 100644
--- a/markdown/extensions/md_in_html.py
+++ b/markdown/extensions/md_in_html.py
@@ -247,8 +247,6 @@ class HTMLExtractorExtra(HTMLExtractor):
 
     def handle_startendtag(self, tag, attrs):
         if tag in self.empty_tags:
-            data = self.get_starttag_text()
-        else:
             attrs = {key: value if value is not None else key for key, value in attrs}
             if "markdown" in attrs:
                 attrs.pop('markdown')
@@ -256,6 +254,8 @@ class HTMLExtractorExtra(HTMLExtractor):
                 data = etree.tostring(element, encoding='unicode', method='html')
             else:
                 data = self.get_starttag_text()
+        else:
+            data = self.get_starttag_text()
         self.handle_empty_tag(data, is_block=self.md.is_block_level(tag))
 
     def handle_data(self, data):
PATCH
