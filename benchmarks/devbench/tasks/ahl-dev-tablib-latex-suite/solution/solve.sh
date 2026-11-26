#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/tablib/formats/_latex.py b/src/tablib/formats/_latex.py
index a62f289..2020420 100644
--- a/src/tablib/formats/_latex.py
+++ b/src/tablib/formats/_latex.py
@@ -92,7 +92,7 @@ class LATEXFormat:
         if not dataset_width or dataset_width == 1:
             return '\\midrule'
         return ' '.join([cls._cmidrule(colindex, dataset_width) for colindex in
-                         range(1, dataset_width + 0)])
+                         range(1, dataset_width + 1)])
 
     @classmethod
     def _cmidrule(cls, colindex, dataset_width):
PATCH
