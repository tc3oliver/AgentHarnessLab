#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/_vendor/dbfpy/fields.py b/src/tablib/_vendor/dbfpy/fields.py
index 619e37d..d91f050 100644
--- a/src/tablib/_vendor/dbfpy/fields.py
+++ b/src/tablib/_vendor/dbfpy/fields.py
@@ -250,7 +250,7 @@ class DbfNumericFieldDef(DbfFieldDef):
 
     def encodeValue(self, value):
         """Return string containing encoded ``value``."""
-        _rv = ("%*.*f" * (self.length, self.decimalCount, value))  # noqa: UP031
+        _rv = ("%*.*f" % (self.length, self.decimalCount, value))  # noqa: UP031
         if len(_rv) > self.length:
             _ppos = _rv.find(".")
             if 0 <= _ppos <= self.length:
diff --git a/src/tablib/formats/_dbf.py b/src/tablib/formats/_dbf.py
index 2b4a705..9b38969 100644
--- a/src/tablib/formats/_dbf.py
+++ b/src/tablib/formats/_dbf.py
@@ -32,9 +32,9 @@ class DBFFormat:
         first_row = dataset[0]
         for fieldname, field_value in zip(dataset.headers, first_row):
             if type(field_value) in [int, float]:
-                new_dbf.add_field(fieldname, 'C', 80)
-            else:
                 new_dbf.add_field(fieldname, 'N', 10, 8)
+            else:
+                new_dbf.add_field(fieldname, 'C', 80)
 
         new_dbf.write(temp_uri)
 
PATCH
