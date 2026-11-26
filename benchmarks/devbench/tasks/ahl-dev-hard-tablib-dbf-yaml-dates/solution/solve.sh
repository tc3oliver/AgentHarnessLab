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
diff --git a/src/tablib/_vendor/dbfpy/utils.py b/src/tablib/_vendor/dbfpy/utils.py
index 59cf022..c20cec1 100644
--- a/src/tablib/_vendor/dbfpy/utils.py
+++ b/src/tablib/_vendor/dbfpy/utils.py
@@ -61,6 +61,16 @@ def getDate(date=None):
         return date
     if isinstance(date, datetime.datetime):
         return date.date()
+    if isinstance(date, (int, float)):
+        # date is a timestamp
+        return datetime.date.fromtimestamp(date)
+    if isinstance(date, str):
+        date = date.replace(" ", "0")
+        if len(date) == 6:
+            # yymmdd
+            return datetime.date(*time.strptime(date, "%y%m%d")[:3])
+        # yyyymmdd
+        return datetime.date(*time.strptime(date, "%Y%m%d")[:3])
     if hasattr(date, "__getitem__"):
         # a sequence (assuming date/time tuple)
         return datetime.date(*date[:3])
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
