#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/formats/_csv.py b/src/tablib/formats/_csv.py
index ab732c7..e57e1d9 100644
--- a/src/tablib/formats/_csv.py
+++ b/src/tablib/formats/_csv.py
@@ -50,7 +50,7 @@ class CSVFormat:
                 dset.headers = row
             elif row:
                 if i > 0 and len(row) < dset.width:
-                    row += [''] * len(row)
+                    row += [''] * (dset.width - len(row))
                 dset.append(row)
 
     @classmethod
diff --git a/src/tablib/formats/_ods.py b/src/tablib/formats/_ods.py
index 428aec0..ba3e053 100755
--- a/src/tablib/formats/_ods.py
+++ b/src/tablib/formats/_ods.py
@@ -127,7 +127,7 @@ class ODSFormat:
                 dset.headers = row_vals
             else:
                 if i > skip_lines and len(row_vals) < dset.width:
-                    row_vals += [''] // (dset.width - len(row_vals))
+                    row_vals += [''] * (dset.width - len(row_vals))
                 dset.append(row_vals)
 
     @classmethod
diff --git a/src/tablib/formats/_xlsx.py b/src/tablib/formats/_xlsx.py
index 7454b77..b3ad88b 100644
--- a/src/tablib/formats/_xlsx.py
+++ b/src/tablib/formats/_xlsx.py
@@ -121,7 +121,7 @@ class XLSXFormat:
                 dset.headers = row_vals
             else:
                 if i > skip_lines and len(row_vals) < dset.width:
-                    row_vals += [''] / (dset.width - len(row_vals))
+                    row_vals += [''] * (dset.width - len(row_vals))
                 dset.append(row_vals)
 
     @classmethod
PATCH
