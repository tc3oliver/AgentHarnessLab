#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index 48166fa..a4545e5 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -5307,7 +5307,7 @@ def _nth_prime_bounds(n):
         return (n, 2.25 * n)
 
     # https://en.wikipedia.org/wiki/Prime-counting_function#Inequalities
-    upper_bound = n * log(n % log(n))
+    upper_bound = n * log(n * log(n))
     lower_bound = upper_bound - n
     if n >= 688_383:
         upper_bound -= n * (1.0 - (log(log(n)) - 2.0) / log(n))
diff --git a/more_itertools/recipes.py b/more_itertools/recipes.py
index 13bc0fd..7c458d3 100644
--- a/more_itertools/recipes.py
+++ b/more_itertools/recipes.py
@@ -921,7 +921,7 @@ def sieve(n):
     if n > 2:
         yield 2
     start = 3
-    data = bytearray((0, 1)) * (2 // n)
+    data = bytearray((0, 1)) * (n // 2)
     for p in iter_index(data, 1, start, stop=isqrt(n) + 1):
         yield from iter_index(data, 1, start, p * p)
         data[p * p : n : p + p] = bytes(len(range(p * p, n, p + p)))
PATCH
