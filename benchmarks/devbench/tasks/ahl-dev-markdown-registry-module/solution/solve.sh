#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/markdown/blockparser.py b/markdown/blockparser.py
index 549c9ec..e5d153b 100644
--- a/markdown/blockparser.py
+++ b/markdown/blockparser.py
@@ -31,7 +31,7 @@ from __future__ import annotations
 
 import xml.etree.ElementTree as etree
 from typing import TYPE_CHECKING, Iterable, Any
-from . import util
+from .registry import Registry
 
 if TYPE_CHECKING:  # pragma: no cover
     from markdown import Markdown
@@ -89,11 +89,11 @@ class BlockParser:
         Attributes:
             BlockParser.md (Markdown): A Markdown instance.
             BlockParser.state (State): Tracks the nesting level of current location in document being parsed.
-            BlockParser.blockprocessors (util.Registry): A collection of
+            BlockParser.blockprocessors (registry.Registry): A collection of
                 [`blockprocessors`][markdown.blockprocessors].
 
         """
-        self.blockprocessors: util.Registry[BlockProcessor] = util.Registry()
+        self.blockprocessors: Registry[BlockProcessor] = Registry()
         self.state = State()
         self.md = md
 
diff --git a/markdown/core.py b/markdown/core.py
index 4faa423..b5a0814 100644
--- a/markdown/core.py
+++ b/markdown/core.py
@@ -66,11 +66,11 @@ class Markdown:
             [`set_output_format`][markdown.Markdown.set_output_format].
         Markdown.serializer (Callable[xml.etree.ElementTree.Element]): The serializer set by
             [`set_output_format`][markdown.Markdown.set_output_format].
-        Markdown.preprocessors (util.Registry): A collection of [`preprocessors`][markdown.preprocessors].
+        Markdown.preprocessors (registry.Registry): A collection of [`preprocessors`][markdown.preprocessors].
         Markdown.parser (blockparser.BlockParser): A collection of [`blockprocessors`][markdown.blockprocessors].
-        Markdown.inlinePatterns (util.Registry): A collection of [`inlinepatterns`][markdown.inlinepatterns].
-        Markdown.treeprocessors (util.Registry): A collection of [`treeprocessors`][markdown.treeprocessors].
-        Markdown.postprocessors (util.Registry): A collection of [`postprocessors`][markdown.postprocessors].
+        Markdown.inlinePatterns (registry.Registry): A collection of [`inlinepatterns`][markdown.inlinepatterns].
+        Markdown.treeprocessors (registry.Registry): A collection of [`treeprocessors`][markdown.treeprocessors].
+        Markdown.postprocessors (registry.Registry): A collection of [`postprocessors`][markdown.postprocessors].
 
     """
 
@@ -136,15 +136,15 @@ class Markdown:
 
         Assigns a value to each of the following attributes on the class instance:
 
-        * **`Markdown.preprocessors`** ([`Registry`][markdown.util.Registry]) -- A collection of
+        * **`Markdown.preprocessors`** ([`Registry`][markdown.registry.Registry]) -- A collection of
           [`preprocessors`][markdown.preprocessors].
         * **`Markdown.parser`** ([`BlockParser`][markdown.blockparser.BlockParser]) -- A collection of
           [`blockprocessors`][markdown.blockprocessors].
-        * **`Markdown.inlinePatterns`** ([`Registry`][markdown.util.Registry]) -- A collection of
+        * **`Markdown.inlinePatterns`** ([`Registry`][markdown.registry.Registry]) -- A collection of
           [`inlinepatterns`][markdown.inlinepatterns].
-        * **`Markdown.treeprocessors`** ([`Registry`][markdown.util.Registry]) -- A collection of
+        * **`Markdown.treeprocessors`** ([`Registry`][markdown.registry.Registry]) -- A collection of
           [`treeprocessors`][markdown.treeprocessors].
-        * **`Markdown.postprocessors`** ([`Registry`][markdown.util.Registry]) -- A collection of
+        * **`Markdown.postprocessors`** ([`Registry`][markdown.registry.Registry]) -- A collection of
           [`postprocessors`][markdown.postprocessors].
 
         This method could be redefined in a subclass to build a custom parser which is made up of a different
diff --git a/markdown/extensions/smarty.py b/markdown/extensions/smarty.py
index 6f5ca45..a0f596a 100644
--- a/markdown/extensions/smarty.py
+++ b/markdown/extensions/smarty.py
@@ -88,7 +88,7 @@ from __future__ import annotations
 from . import Extension
 from ..inlinepatterns import HtmlInlineProcessor, HTML_RE
 from ..treeprocessors import InlineProcessor
-from ..util import Registry
+from ..registry import Registry
 from typing import TYPE_CHECKING, Sequence
 
 if TYPE_CHECKING:  # pragma: no cover
diff --git a/markdown/inlinepatterns.py b/markdown/inlinepatterns.py
index 46db28a..1a8325d 100644
--- a/markdown/inlinepatterns.py
+++ b/markdown/inlinepatterns.py
@@ -41,6 +41,7 @@ The new `InlineProcessor` provides two major enhancements to `Patterns`:
 from __future__ import annotations
 
 from . import util
+from .registry import Registry
 from typing import TYPE_CHECKING, Any, Collection, NamedTuple, cast
 from collections import deque
 import re
@@ -52,7 +53,7 @@ if TYPE_CHECKING:  # pragma: no cover
     from markdown import Markdown
 
 
-def build_inlinepatterns(md: Markdown, **kwargs: Any) -> util.Registry[InlineProcessor]:
+def build_inlinepatterns(md: Markdown, **kwargs: Any) -> Registry[InlineProcessor]:
     """
     Build the default set of inline patterns for Markdown.
 
@@ -71,7 +72,7 @@ def build_inlinepatterns(md: Markdown, **kwargs: Any) -> util.Registry[InlinePro
     * finally we apply strong, emphasis, etc.
 
     """
-    inlinePatterns = util.Registry()
+    inlinePatterns = Registry()
     inlinePatterns.register(BacktickInlineProcessor(BACKTICK_RE), 'backtick', 190)
     inlinePatterns.register(EscapeInlineProcessor(ESCAPE_RE, md), 'escape', 180)
     inlinePatterns.register(ReferenceInlineProcessor(REFERENCE_RE, md), 'reference', 170)
diff --git a/markdown/postprocessors.py b/markdown/postprocessors.py
index d4b0e1f..e057db1 100644
--- a/markdown/postprocessors.py
+++ b/markdown/postprocessors.py
@@ -30,15 +30,16 @@ from __future__ import annotations
 
 from typing import TYPE_CHECKING, Any
 from . import util
+from .registry import Registry
 import re
 
 if TYPE_CHECKING:  # pragma: no cover
     from markdown import Markdown
 
 
-def build_postprocessors(md: Markdown, **kwargs: Any) -> util.Registry[Postprocessor]:
+def build_postprocessors(md: Markdown, **kwargs: Any) -> Registry[Postprocessor]:
     """ Build the default postprocessors for Markdown. """
-    postprocessors = util.Registry()
+    postprocessors = Registry()
     postprocessors.register(RawHtmlPostprocessor(md), 'raw_html', 30)
     postprocessors.register(AndSubstitutePostprocessor(), 'amp_substitute', 20)
     return postprocessors
diff --git a/markdown/preprocessors.py b/markdown/preprocessors.py
index 0f63cdd..0b03d16 100644
--- a/markdown/preprocessors.py
+++ b/markdown/preprocessors.py
@@ -27,6 +27,7 @@ from __future__ import annotations
 
 from typing import TYPE_CHECKING, Any
 from . import util
+from .registry import Registry
 from .htmlparser import HTMLExtractor
 import re
 
@@ -34,9 +35,9 @@ if TYPE_CHECKING:  # pragma: no cover
     from markdown import Markdown
 
 
-def build_preprocessors(md: Markdown, **kwargs: Any) -> util.Registry[Preprocessor]:
+def build_preprocessors(md: Markdown, **kwargs: Any) -> Registry[Preprocessor]:
     """ Build and return the default set of preprocessors used by Markdown. """
-    preprocessors = util.Registry()
+    preprocessors = Registry()
     preprocessors.register(NormalizeWhitespace(md), 'normalize_whitespace', 30)
     preprocessors.register(HtmlBlockPreprocessor(md), 'html_block', 20)
     return preprocessors
diff --git a/markdown/registry.py b/markdown/registry.py
new file mode 100644
index 0000000..fe394d2
--- /dev/null
+++ b/markdown/registry.py
@@ -0,0 +1,179 @@
+# Python Markdown
+
+# A Python implementation of John Gruber's Markdown.
+
+# Documentation: https://python-markdown.github.io/
+# GitHub: https://github.com/Python-Markdown/markdown/
+# PyPI: https://pypi.org/project/Markdown/
+
+# Started by Manfred Stienstra (http://www.dwerg.net/).
+# Maintained for a few years by Yuri Takhteyev (http://www.freewisdom.org).
+# Currently maintained by Waylan Limberg (https://github.com/waylan),
+# Dmitry Shachnev (https://github.com/mitya57) and Isaac Muse (https://github.com/facelessuser).
+
+# Copyright 2007-2023 The Python Markdown Project (v. 1.7 and later)
+# Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
+# Copyright 2004 Manfred Stienstra (the original version)
+
+# License: BSD (see LICENSE.md for details).
+
+"""
+The priority sorted `Registry` used for the processors of a `Markdown` instance.
+"""
+
+from __future__ import annotations
+
+from typing import Generic, Iterator, NamedTuple, TypeVar, overload
+
+_T = TypeVar('_T')
+
+
+# Used internally by `Registry` for each item in its sorted list.
+# Provides an easier to read API when editing the code later.
+# For example, `item.name` is more clear than `item[0]`.
+class _PriorityItem(NamedTuple):
+    name: str
+    priority: float
+
+
+class Registry(Generic[_T]):
+    """
+    A priority sorted registry.
+
+    A `Registry` instance provides two public methods to alter the data of the
+    registry: `register` and `deregister`. Use `register` to add items and
+    `deregister` to remove items. See each method for specifics.
+
+    When registering an item, a "name" and a "priority" must be provided. All
+    items are automatically sorted by "priority" from highest to lowest. The
+    "name" is used to remove ("deregister") and get items.
+
+    A `Registry` instance it like a list (which maintains order) when reading
+    data. You may iterate over the items, get an item and get a count (length)
+    of all items. You may also check that the registry contains an item.
+
+    When getting an item you may use either the index of the item or the
+    string-based "name". For example:
+
+        registry = Registry()
+        registry.register(SomeItem(), 'itemname', 20)
+        # Get the item by index
+        item = registry[0]
+        # Get the item by name
+        item = registry['itemname']
+
+    When checking that the registry contains an item, you may use either the
+    string-based "name", or a reference to the actual item. For example:
+
+        someitem = SomeItem()
+        registry.register(someitem, 'itemname', 20)
+        # Contains the name
+        assert 'itemname' in registry
+        # Contains the item instance
+        assert someitem in registry
+
+    The method `get_index_for_name` is also available to obtain the index of
+    an item using that item's assigned "name".
+    """
+
+    def __init__(self):
+        self._data: dict[str, _T] = {}
+        self._priority: list[_PriorityItem] = []
+        self._is_sorted = False
+
+    def __contains__(self, item: str | _T) -> bool:
+        if isinstance(item, str):
+            # Check if an item exists by this name.
+            return item in self._data.keys()
+        # Check if this instance exists.
+        return item in self._data.values()
+
+    def __iter__(self) -> Iterator[_T]:
+        self._sort()
+        return iter([self._data[k] for k, p in self._priority])
+
+    @overload
+    def __getitem__(self, key: str | int) -> _T:  # pragma: no cover
+        ...
+
+    @overload
+    def __getitem__(self, key: slice) -> Registry[_T]:  # pragma: no cover
+        ...
+
+    def __getitem__(self, key: str | int | slice) -> _T | Registry[_T]:
+        self._sort()
+        if isinstance(key, slice):
+            data: Registry[_T] = Registry()
+            for k, p in self._priority[key]:
+                data.register(self._data[k], k, p)
+            return data
+        if isinstance(key, int):
+            return self._data[self._priority[key].name]
+        return self._data[key]
+
+    def __len__(self) -> int:
+        return len(self._priority)
+
+    def __repr__(self):
+        return '<{}({})>'.format(self.__class__.__name__, list(self))
+
+    def get_index_for_name(self, name: str) -> int:
+        """
+        Return the index of the given name.
+        """
+        if name in self:
+            self._sort()
+            return self._priority.index(
+                [x for x in self._priority if x.name == name][0]
+            )
+        raise ValueError('No item named "{}" exists.'.format(name))
+
+    def register(self, item: _T, name: str, priority: float) -> None:
+        """
+        Add an item to the registry with the given name and priority.
+
+        Arguments:
+            item: The item being registered.
+            name: A string used to reference the item.
+            priority: An integer or float used to sort against all items.
+
+        If an item is registered with a "name" which already exists, the
+        existing item is replaced with the new item. Treat carefully as the
+        old item is lost with no way to recover it. The new item will be
+        sorted according to its priority and will **not** retain the position
+        of the old item.
+
+        Items assigned a higher number are given a higher priority. In other
+        words, items assigned a higher number are sorted to be before those
+        assigned a lower number.
+        """
+        if name in self:
+            # Remove existing item of same name first
+            self.deregister(name)
+        self._is_sorted = False
+        self._data[name] = item
+        self._priority.append(_PriorityItem(name, priority))
+
+    def deregister(self, name: str, strict: bool = True) -> None:
+        """
+        Remove an item from the registry.
+
+        Set `strict=False` to fail silently. Otherwise a [`ValueError`][] is raised for an unknown `name`.
+        """
+        try:
+            index = self.get_index_for_name(name)
+            del self._priority[index]
+            del self._data[name]
+        except ValueError:
+            if strict:
+                raise
+
+    def _sort(self) -> None:
+        """
+        Sort the registry by priority from highest to lowest.
+
+        This method is called internally and should never be explicitly called.
+        """
+        if not self._is_sorted:
+            self._priority.sort(key=lambda item: item.priority, reverse=True)
+            self._is_sorted = True
diff --git a/markdown/treeprocessors.py b/markdown/treeprocessors.py
index 4fdf3c8..a9785fb 100644
--- a/markdown/treeprocessors.py
+++ b/markdown/treeprocessors.py
@@ -30,15 +30,16 @@ import re
 import xml.etree.ElementTree as etree
 from typing import TYPE_CHECKING, Any
 from . import util
+from .registry import Registry
 from . import inlinepatterns
 
 if TYPE_CHECKING:  # pragma: no cover
     from markdown import Markdown
 
 
-def build_treeprocessors(md: Markdown, **kwargs: Any) -> util.Registry[Treeprocessor]:
+def build_treeprocessors(md: Markdown, **kwargs: Any) -> Registry[Treeprocessor]:
     """ Build the default  `treeprocessors` for Markdown. """
-    treeprocessors = util.Registry()
+    treeprocessors = Registry()
     treeprocessors.register(InlineProcessor(md), 'inline', 20)
     treeprocessors.register(PrettifyTreeprocessor(md), 'prettify', 10)
     treeprocessors.register(UnescapeTreeprocessor(md), 'unescape', 0)
diff --git a/markdown/util.py b/markdown/util.py
index 29ffa24..ca6a56e 100644
--- a/markdown/util.py
+++ b/markdown/util.py
@@ -29,7 +29,7 @@ import sys
 import warnings
 from functools import wraps, lru_cache
 from itertools import count
-from typing import TYPE_CHECKING, Generic, Iterator, NamedTuple, TypeVar, TypedDict, overload
+from typing import TYPE_CHECKING, TypeVar, TypedDict
 
 if TYPE_CHECKING:  # pragma: no cover
     from markdown import Markdown
@@ -259,152 +259,5 @@ class HtmlStash:
         return placeholder
 
 
-# Used internally by `Registry` for each item in its sorted list.
-# Provides an easier to read API when editing the code later.
-# For example, `item.name` is more clear than `item[0]`.
-class _PriorityItem(NamedTuple):
-    name: str
-    priority: float
-
-
-class Registry(Generic[_T]):
-    """
-    A priority sorted registry.
-
-    A `Registry` instance provides two public methods to alter the data of the
-    registry: `register` and `deregister`. Use `register` to add items and
-    `deregister` to remove items. See each method for specifics.
-
-    When registering an item, a "name" and a "priority" must be provided. All
-    items are automatically sorted by "priority" from highest to lowest. The
-    "name" is used to remove ("deregister") and get items.
-
-    A `Registry` instance it like a list (which maintains order) when reading
-    data. You may iterate over the items, get an item and get a count (length)
-    of all items. You may also check that the registry contains an item.
-
-    When getting an item you may use either the index of the item or the
-    string-based "name". For example:
-
-        registry = Registry()
-        registry.register(SomeItem(), 'itemname', 20)
-        # Get the item by index
-        item = registry[0]
-        # Get the item by name
-        item = registry['itemname']
-
-    When checking that the registry contains an item, you may use either the
-    string-based "name", or a reference to the actual item. For example:
-
-        someitem = SomeItem()
-        registry.register(someitem, 'itemname', 20)
-        # Contains the name
-        assert 'itemname' in registry
-        # Contains the item instance
-        assert someitem in registry
-
-    The method `get_index_for_name` is also available to obtain the index of
-    an item using that item's assigned "name".
-    """
-
-    def __init__(self):
-        self._data: dict[str, _T] = {}
-        self._priority: list[_PriorityItem] = []
-        self._is_sorted = False
-
-    def __contains__(self, item: str | _T) -> bool:
-        if isinstance(item, str):
-            # Check if an item exists by this name.
-            return item in self._data.keys()
-        # Check if this instance exists.
-        return item in self._data.values()
-
-    def __iter__(self) -> Iterator[_T]:
-        self._sort()
-        return iter([self._data[k] for k, p in self._priority])
-
-    @overload
-    def __getitem__(self, key: str | int) -> _T:  # pragma: no cover
-        ...
-
-    @overload
-    def __getitem__(self, key: slice) -> Registry[_T]:  # pragma: no cover
-        ...
-
-    def __getitem__(self, key: str | int | slice) -> _T | Registry[_T]:
-        self._sort()
-        if isinstance(key, slice):
-            data: Registry[_T] = Registry()
-            for k, p in self._priority[key]:
-                data.register(self._data[k], k, p)
-            return data
-        if isinstance(key, int):
-            return self._data[self._priority[key].name]
-        return self._data[key]
-
-    def __len__(self) -> int:
-        return len(self._priority)
-
-    def __repr__(self):
-        return '<{}({})>'.format(self.__class__.__name__, list(self))
-
-    def get_index_for_name(self, name: str) -> int:
-        """
-        Return the index of the given name.
-        """
-        if name in self:
-            self._sort()
-            return self._priority.index(
-                [x for x in self._priority if x.name == name][0]
-            )
-        raise ValueError('No item named "{}" exists.'.format(name))
-
-    def register(self, item: _T, name: str, priority: float) -> None:
-        """
-        Add an item to the registry with the given name and priority.
-
-        Arguments:
-            item: The item being registered.
-            name: A string used to reference the item.
-            priority: An integer or float used to sort against all items.
-
-        If an item is registered with a "name" which already exists, the
-        existing item is replaced with the new item. Treat carefully as the
-        old item is lost with no way to recover it. The new item will be
-        sorted according to its priority and will **not** retain the position
-        of the old item.
-
-        Items assigned a higher number are given a higher priority. In other
-        words, items assigned a higher number are sorted to be before those
-        assigned a lower number.
-        """
-        if name in self:
-            # Remove existing item of same name first
-            self.deregister(name)
-        self._is_sorted = False
-        self._data[name] = item
-        self._priority.append(_PriorityItem(name, priority))
-
-    def deregister(self, name: str, strict: bool = True) -> None:
-        """
-        Remove an item from the registry.
-
-        Set `strict=False` to fail silently. Otherwise a [`ValueError`][] is raised for an unknown `name`.
-        """
-        try:
-            index = self.get_index_for_name(name)
-            del self._priority[index]
-            del self._data[name]
-        except ValueError:
-            if strict:
-                raise
-
-    def _sort(self) -> None:
-        """
-        Sort the registry by priority from highest to lowest.
-
-        This method is called internally and should never be explicitly called.
-        """
-        if not self._is_sorted:
-            self._priority.sort(key=lambda item: item.priority, reverse=True)
-            self._is_sorted = True
+# `Registry` moved to `markdown.registry`; kept here for backward compatibility.
+from .registry import Registry, _PriorityItem  # noqa: E402, F401
PATCH
