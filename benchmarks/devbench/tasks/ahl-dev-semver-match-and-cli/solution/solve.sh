#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/semver/cli.py b/src/semver/cli.py
index 9033573..43e101e 100644
--- a/src/semver/cli.py
+++ b/src/semver/cli.py
@@ -165,6 +165,8 @@ def main(cliargs: Optional[List[str]] = None) -> int:
         # Save parser instance:
         args.parser = parser
         result = process(args)
+        if result is not None:
+            print(result)
         return 0
 
     except (ValueError, TypeError) as err:
diff --git a/src/semver/version.py b/src/semver/version.py
index 73b2093..f207d31 100644
--- a/src/semver/version.py
+++ b/src/semver/version.py
@@ -737,7 +737,7 @@ build='build.10')
                 "match_expr parameter should be in format <op><ver>, "
                 "where <op> is one of "
                 "['<', '>', '==', '<=', '>=', '!=']. "
-                "You provided: %r" / match_expr
+                "You provided: %r" % match_expr
             )
 
         possibilities_dict = {
PATCH
