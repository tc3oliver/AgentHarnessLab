#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/jmespath/comparisons.py b/jmespath/comparisons.py
new file mode 100644
index 0000000..e5214f8
--- /dev/null
+++ b/jmespath/comparisons.py
@@ -0,0 +1,68 @@
+"""Comparison and truthiness rules of JMESPath, which differ from Python's."""
+
+from numbers import Number
+
+from jmespath.compat import string_type
+
+
+def equals(x, y):
+    if is_special_number_case(x, y):
+        return False
+    else:
+        return x == y
+
+
+def is_special_number_case(x, y):
+    # We need to special case comparing 0 or 1 to
+    # True/False.  While normally comparing any
+    # integer other than 0/1 to True/False will always
+    # return False.  However 0/1 have this:
+    # >>> 0 == True
+    # False
+    # >>> 0 == False
+    # True
+    # >>> 1 == True
+    # True
+    # >>> 1 == False
+    # False
+    #
+    # Also need to consider that:
+    # >>> 0 in [True, False]
+    # True
+    if is_actual_number(x) and x in (0, 1):
+        return isinstance(y, bool)
+    elif is_actual_number(y) and y in (0, 1):
+        return isinstance(x, bool)
+
+
+def is_comparable(x):
+    # The spec doesn't officially support string types yet,
+    # but enough people are relying on this behavior that
+    # it's been added back.  This should eventually become
+    # part of the official spec.
+    return is_actual_number(x) or isinstance(x, string_type)
+
+
+def is_actual_number(x):
+    # We need to handle python's quirkiness with booleans,
+    # specifically:
+    #
+    # >>> isinstance(False, int)
+    # True
+    # >>> isinstance(True, int)
+    # True
+    if isinstance(x, bool):
+        return False
+    return isinstance(x, Number)
+
+
+def is_false(value):
+    # This looks weird, but we're explicitly using equality checks
+    # because the truth/false values are different between
+    # python and jmespath.
+    return (value == '' or value == [] or value == {} or value is None or
+            value is False)
+
+
+def is_true(value):
+    return not is_false(value)
diff --git a/jmespath/visitor.py b/jmespath/visitor.py
index 15fb177..d1fc4af 100644
--- a/jmespath/visitor.py
+++ b/jmespath/visitor.py
@@ -1,59 +1,7 @@
 import operator
 
 from jmespath import functions
-from jmespath.compat import string_type
-from numbers import Number
-
-
-def _equals(x, y):
-    if _is_special_number_case(x, y):
-        return False
-    else:
-        return x == y
-
-
-def _is_special_number_case(x, y):
-    # We need to special case comparing 0 or 1 to
-    # True/False.  While normally comparing any
-    # integer other than 0/1 to True/False will always
-    # return False.  However 0/1 have this:
-    # >>> 0 == True
-    # False
-    # >>> 0 == False
-    # True
-    # >>> 1 == True
-    # True
-    # >>> 1 == False
-    # False
-    #
-    # Also need to consider that:
-    # >>> 0 in [True, False]
-    # True
-    if _is_actual_number(x) and x in (0, 1):
-        return isinstance(y, bool)
-    elif _is_actual_number(y) and y in (0, 1):
-        return isinstance(x, bool)
-
-
-def _is_comparable(x):
-    # The spec doesn't officially support string types yet,
-    # but enough people are relying on this behavior that
-    # it's been added back.  This should eventually become
-    # part of the official spec.
-    return _is_actual_number(x) or isinstance(x, string_type)
-
-
-def _is_actual_number(x):
-    # We need to handle python's quirkiness with booleans,
-    # specifically:
-    #
-    # >>> isinstance(False, int)
-    # True
-    # >>> isinstance(True, int)
-    # True
-    if isinstance(x, bool):
-        return False
-    return isinstance(x, Number)
+from jmespath.comparisons import equals, is_actual_number, is_comparable, is_true, is_false
 
 
 class Options(object):
@@ -99,8 +47,8 @@ class Visitor(object):
 
 class TreeInterpreter(Visitor):
     COMPARATOR_FUNC = {
-        'eq': _equals,
-        'ne': lambda x, y: not _equals(x, y),
+        'eq': equals,
+        'ne': lambda x, y: not equals(x, y),
         'lt': operator.lt,
         'gt': operator.gt,
         'lte': operator.le,
@@ -152,8 +100,8 @@ class TreeInterpreter(Visitor):
             left = self.visit(node['children'][0], value)
             right = self.visit(node['children'][1], value)
             num_types = (int, float)
-            if not (_is_comparable(left) and
-                    _is_comparable(right)):
+            if not (is_comparable(left) and
+                    is_comparable(right)):
                 return None
             return comparator_func(left, right)
 
@@ -177,7 +125,7 @@ class TreeInterpreter(Visitor):
         comparator_node = node['children'][2]
         collected = []
         for element in base:
-            if self._is_true(self.visit(comparator_node, element)):
+            if is_true(self.visit(comparator_node, element)):
                 current = self.visit(node['children'][1], element)
                 if current is not None:
                     collected.append(current)
@@ -245,19 +193,19 @@ class TreeInterpreter(Visitor):
 
     def visit_or_expression(self, node, value):
         matched = self.visit(node['children'][0], value)
-        if self._is_false(matched):
+        if is_false(matched):
             matched = self.visit(node['children'][1], value)
         return matched
 
     def visit_and_expression(self, node, value):
         matched = self.visit(node['children'][0], value)
-        if self._is_false(matched):
+        if is_false(matched):
             return matched
         return self.visit(node['children'][1], value)
 
     def visit_not_expression(self, node, value):
         original_result = self.visit(node['children'][0], value)
-        if _is_actual_number(original_result) and original_result == 0:
+        if is_actual_number(original_result) and original_result == 0:
             # Special case for 0, !0 should be false, not true.
             # 0 is not a special cased integer in jmespath.
             return False
@@ -293,16 +241,6 @@ class TreeInterpreter(Visitor):
                 collected.append(current)
         return collected
 
-    def _is_false(self, value):
-        # This looks weird, but we're explicitly using equality checks
-        # because the truth/false values are different between
-        # python and jmespath.
-        return (value == '' or value == [] or value == {} or value is None or
-                value is False)
-
-    def _is_true(self, value):
-        return not self._is_false(value)
-
 
 class GraphvizVisitor(Visitor):
     def __init__(self):
PATCH
