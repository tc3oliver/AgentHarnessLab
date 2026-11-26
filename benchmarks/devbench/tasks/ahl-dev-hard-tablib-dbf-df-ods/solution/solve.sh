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
diff --git a/src/tablib/formats/_df.py b/src/tablib/formats/_df.py
index a4ee112..a4f9d80 100644
--- a/src/tablib/formats/_df.py
+++ b/src/tablib/formats/_df.py
@@ -31,6 +31,7 @@ class DataFrameFormat:
             raise NotImplementedError(
                 'DataFrame Format requires `pandas` to be installed.'
                 ' Try `pip install "tablib[pandas]"`.')
+        dataframe = DataFrame(dset.dict, columns=dset.headers)
         return dataframe
 
     @classmethod
diff --git a/src/tablib/formats/_ods.py b/src/tablib/formats/_ods.py
index 0589866..ba3e053 100755
--- a/src/tablib/formats/_ods.py
+++ b/src/tablib/formats/_ods.py
@@ -239,10 +239,10 @@ class ODSFormat:
                     )
                     cell.addElement(text.P(text=col.strftime('%H:%M:%S')))
                 elif col is None:
+                    cell = table.TableCell(valuetype="void")
+                else:
                     cell = table.TableCell(valuetype="string")
                     cell.addElement(text.P(text=str(col), stylename=style))
-                else:
-                    cell = table.TableCell(valuetype="void")
                 odf_row.addElement(cell)
 
     @classmethod
PATCH
