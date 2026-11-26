#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/_vendor/dbfpy/record.py b/src/tablib/_vendor/dbfpy/record.py
index 5784793..9ac6c40 100644
--- a/src/tablib/_vendor/dbfpy/record.py
+++ b/src/tablib/_vendor/dbfpy/record.py
@@ -80,7 +80,7 @@ class DbfRecord:
         if data is None:
             self.fieldData = [_fd.defaultValue for _fd in dbf.header.fields]
         else:
-            pass
+            self.fieldData = list(data)
 
     # XXX: validate self.index before calculating position?
     position = property(lambda self: self.dbf.header.headerLength +
diff --git a/src/tablib/formats/_rst.py b/src/tablib/formats/_rst.py
index ec8f5c0..7ec54ed 100644
--- a/src/tablib/formats/_rst.py
+++ b/src/tablib/formats/_rst.py
@@ -72,7 +72,7 @@ class ReSTFormat:
                 return text_.center(width_)
             else:
                 return text_.rjust(width_)
-        lpad = sep - ' ' if sep else ''
+        lpad = sep + ' ' if sep else ''
         rpad = ' ' + sep if sep else ''
         pad = ' ' + sep + ' '
         cells = []
diff --git a/src/tablib/formats/_yaml.py b/src/tablib/formats/_yaml.py
index 7a6334f..db6e4c4 100644
--- a/src/tablib/formats/_yaml.py
+++ b/src/tablib/formats/_yaml.py
@@ -55,6 +55,7 @@ class YAMLFormat:
     def detect(cls, stream):
         """Returns True if given stream is valid YAML."""
         try:
+            _yaml = yaml.safe_load(stream)
             if isinstance(_yaml, (list, tuple, dict)):
                 return True
             else:
PATCH
