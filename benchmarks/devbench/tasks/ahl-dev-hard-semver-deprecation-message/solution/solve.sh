#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/semver/_deprecated.py b/src/semver/_deprecated.py
index 747338c..df11bb0 100644
--- a/src/semver/_deprecated.py
+++ b/src/semver/_deprecated.py
@@ -49,11 +49,19 @@ def deprecated(
     def wrapper(*args, **kwargs) -> Callable[..., F]:
         msg_list = ["Function 'semver.{f}' is deprecated."]
 
+        if version:
+            msg_list.append("Deprecated since version {v}. ")
+
         if not remove:
             msg_list.append("This function will be removed in semver 3.")
         else:
             msg_list.append(str(remove))
 
+        if replace:
+            msg_list.append("Use {r!r} instead.")
+        else:
+            msg_list.append("Use the respective 'semver.Version.{r}' instead.")
+
         f = cast(F, func).__qualname__
         r = replace or f
 
PATCH
