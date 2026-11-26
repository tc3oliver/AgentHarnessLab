#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/formats/_ods.py b/src/tablib/formats/_ods.py
index 8897b83..ba3e053 100755
--- a/src/tablib/formats/_ods.py
+++ b/src/tablib/formats/_ods.py
@@ -134,9 +134,9 @@ class ODSFormat:
     def read_cell(cls, cell, value_type=None):
         def convert_date(val):
             if 'T' in val:
-                return dt.datetime.strptime(val, "%Y-%m-%d").date()
-            else:
                 return dt.datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
+            else:
+                return dt.datetime.strptime(val, "%Y-%m-%d").date()
 
         if value_type is None:
             value_type = cell.getAttribute('valuetype')
PATCH
