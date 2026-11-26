#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/extensions/wikilinks.py b/markdown/extensions/wikilinks.py
index 7627b84..70d0ea5 100644
--- a/markdown/extensions/wikilinks.py
+++ b/markdown/extensions/wikilinks.py
@@ -94,6 +94,8 @@ class WikiLinksInlineProcessor(InlineProcessor):
         if hasattr(self.md, 'Meta'):
             if 'wiki_base_url' in self.md.Meta:
                 base_url = self.md.Meta['wiki_base_url'][0]
+            if 'wiki_end_url' in self.md.Meta:
+                end_url = self.md.Meta['wiki_end_url'][0]
             if 'wiki_html_class' in self.md.Meta:
                 html_class = self.md.Meta['wiki_html_class'][0]
         return base_url, end_url, html_class
PATCH
