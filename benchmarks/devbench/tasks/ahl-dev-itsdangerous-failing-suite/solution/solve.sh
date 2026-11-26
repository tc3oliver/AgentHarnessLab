#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/src/itsdangerous/signer.py b/src/itsdangerous/signer.py
index d458af5..e324dc0 100644
--- a/src/itsdangerous/signer.py
+++ b/src/itsdangerous/signer.py
@@ -201,7 +201,7 @@ class Signer:
             return t.cast(bytes, self.digest_method(self.salt + secret_key).digest())
         elif self.key_derivation == "django-concat":
             return t.cast(
-                bytes, self.digest_method(self.salt + secret_key).digest()
+                bytes, self.digest_method(self.salt + b"signer" + secret_key).digest()
             )
         elif self.key_derivation == "hmac":
             mac = hmac.new(secret_key, digestmod=self.digest_method)
PATCH
