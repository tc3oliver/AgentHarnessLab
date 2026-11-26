#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/_vendor/dbfpy/header.py b/src/tablib/_vendor/dbfpy/header.py
index 2c94a8f..4032918 100644
--- a/src/tablib/_vendor/dbfpy/header.py
+++ b/src/tablib/_vendor/dbfpy/header.py
@@ -240,6 +240,18 @@ Version (signature): 0x%02x
         stream.write(b'\x0D')   # cr at end of all header data
         self.changed = False
 
+    def toString(self):
+        """Returned 32 chars length string with encoded header."""
+        return struct.pack("<4BI2H",
+                           self.signature,
+                           self.year - 1900,
+                           self.month,
+                           self.day,
+                           self.recordCount,
+                           self.headerLength,
+                           self.recordLength) + (b'\x00' * 20)
+        # TODO: figure out if bytes(utf-8) is correct here.
+
     def setCurrentDate(self):
         """Update ``self.lastUpdate`` field with current date value."""
         self.lastUpdate = datetime.date.today()
diff --git a/src/tablib/formats/_ods.py b/src/tablib/formats/_ods.py
index e70828c..ba3e053 100755
--- a/src/tablib/formats/_ods.py
+++ b/src/tablib/formats/_ods.py
@@ -133,7 +133,10 @@ class ODSFormat:
     @classmethod
     def read_cell(cls, cell, value_type=None):
         def convert_date(val):
-            pass
+            if 'T' in val:
+                return dt.datetime.strptime(val, "%Y-%m-%dT%H:%M:%S")
+            else:
+                return dt.datetime.strptime(val, "%Y-%m-%d").date()
 
         if value_type is None:
             value_type = cell.getAttribute('valuetype')
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
PATCH
