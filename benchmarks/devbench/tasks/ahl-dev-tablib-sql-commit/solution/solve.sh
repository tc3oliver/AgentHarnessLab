#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/formats/_sql.py b/src/tablib/formats/_sql.py
index c7b1ae3..e4ec8f9 100644
--- a/src/tablib/formats/_sql.py
+++ b/src/tablib/formats/_sql.py
@@ -64,7 +64,7 @@ class SQLFormat:
             statements.append(
                 f'INSERT INTO {tbl_ident}{columns_headers} VALUES ({values});'
             )
-        return '\n'.join(statements) + ('COMMIT;\n' if commit else '')
+        return '\n'.join(statements) + '\n' + ('COMMIT;\n' if commit else '')
 
     @classmethod
     def import_set(cls, dataset, in_stream, **kwargs):
PATCH
