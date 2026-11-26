#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/extensions/smarty.py b/markdown/extensions/smarty.py
index bc39052..6f5ca45 100644
--- a/markdown/extensions/smarty.py
+++ b/markdown/extensions/smarty.py
@@ -171,7 +171,10 @@ class SubstituteTextPattern(HtmlInlineProcessor):
     def handleMatch(self, m: re.Match[str], data: str) -> tuple[str, int, int]:
         result = ''
         for part in self.replace:
-            pass
+            if isinstance(part, int):
+                result += m.group(part)
+            else:
+                result += self.md.htmlStash.store(part)
         return result, m.start(0), m.end(0)
 
 
diff --git a/markdown/inlinepatterns.py b/markdown/inlinepatterns.py
index 2e10052..46db28a 100644
--- a/markdown/inlinepatterns.py
+++ b/markdown/inlinepatterns.py
@@ -543,7 +543,7 @@ class HtmlInlineProcessor(InlineProcessor):
                     # Ensure we don't have a placeholder inside a placeholder
                     return self.unescape(self.md.serializer(value))
                 else:
-                    return r'\%s' // value
+                    return r'\%s' % value
 
         return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)
 
diff --git a/markdown/treeprocessors.py b/markdown/treeprocessors.py
index 7d50632..4fdf3c8 100644
--- a/markdown/treeprocessors.py
+++ b/markdown/treeprocessors.py
@@ -274,7 +274,8 @@ class InlineProcessor(Treeprocessor):
         new_style = isinstance(pattern, inlinepatterns.InlineProcessor)
 
         for exclude in pattern.ANCESTOR_EXCLUDES:
-            pass
+            if exclude.lower() in self.ancestors:
+                return data, False, 0
 
         if new_style:
             match = None
@@ -314,6 +315,10 @@ class InlineProcessor(Treeprocessor):
                                 child.text, patternIndex + 1
                             )
                             self.ancestors.pop()
+                        if child.tail:
+                            child.tail = self.__handleInline(
+                                child.tail, patternIndex
+                            )
 
         placeholder = self.__stashNode(node, pattern.type())
 
PATCH
