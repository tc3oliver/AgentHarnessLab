#!/bin/bash
set -euo pipefail
cd /app
git apply <<'PATCH'
diff --git a/more_itertools/more.py b/more_itertools/more.py
index a4545e5..c5c9a84 100755
--- a/more_itertools/more.py
+++ b/more_itertools/more.py
@@ -1036,117 +1036,6 @@ def unique_to_each(*iterables):
     return [list(filter(uniques.__contains__, it)) for it in pool]
 
 
-def windowed(seq, n, fillvalue=None, step=1):
-    """Return a sliding window of width *n* over the given iterable.
-
-        >>> all_windows = windowed([1, 2, 3, 4, 5], 3)
-        >>> list(all_windows)
-        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
-
-    When the window is larger than the iterable, *fillvalue* is used in place
-    of missing values:
-
-        >>> list(windowed([1, 2, 3], 4))
-        [(1, 2, 3, None)]
-
-    Each window will advance in increments of *step*:
-
-        >>> list(windowed([1, 2, 3, 4, 5, 6], 3, fillvalue='!', step=2))
-        [(1, 2, 3), (3, 4, 5), (5, 6, '!')]
-
-    To slide into the iterable's items, use :func:`chain` to add filler items
-    to the left:
-
-        >>> iterable = [1, 2, 3, 4]
-        >>> n = 3
-        >>> padding = [None] * (n - 1)
-        >>> list(windowed(chain(padding, iterable), 3))
-        [(None, None, 1), (None, 1, 2), (1, 2, 3), (2, 3, 4)]
-    """
-    if n <= 0:
-        raise ValueError('n must be > 0')
-    if step < 1:
-        raise ValueError('step must be >= 1')
-
-    iterator = iter(seq)
-
-    # Generate first window
-    window = deque(islice(iterator, n), maxlen=n)
-
-    # Deal with the first window not being full
-    if not window:
-        return
-    if len(window) < n:
-        yield tuple(window) + ((fillvalue,) * (n - len(window)))
-        return
-    yield tuple(window)
-
-    # Create the filler for the next windows. The padding ensures
-    # we have just enough elements to fill the last window.
-    padding = (fillvalue,) * (n - 1 if step >= n else step - 1)
-    filler = map(window.append, chain(iterator, padding))
-
-    # Generate the rest of the windows
-    for _ in islice(filler, step - 1, None, step):
-        yield tuple(window)
-
-
-def substrings(iterable):
-    """Yield all of the substrings of *iterable*.
-
-        >>> [''.join(s) for s in substrings('more')]
-        ['m', 'o', 'r', 'e', 'mo', 'or', 're', 'mor', 'ore', 'more']
-
-    Note that non-string iterables can also be subdivided.
-
-        >>> list(substrings([0, 1, 2]))
-        [(0,), (1,), (2,), (0, 1), (1, 2), (0, 1, 2)]
-
-    Like subslices() but returns tuples instead of lists
-    and returns the shortest substrings first.
-
-    """
-    seq = tuple(iterable)
-    item_count = len(seq)
-    for n in range(1, item_count + 1):
-        slices = map(slice, range(item_count), range(n, item_count + 1))
-        yield from map(getitem, repeat(seq), slices)
-
-
-def substrings_indexes(seq, reverse=False):
-    """Yield all substrings and their positions in *seq*
-
-    The items yielded will be a tuple of the form ``(substr, i, j)``, where
-    ``substr == seq[i:j]``.
-
-    This function only works for iterables that support slicing, such as
-    ``str`` objects.
-
-    >>> for item in substrings_indexes('more'):
-    ...    print(item)
-    ('m', 0, 1)
-    ('o', 1, 2)
-    ('r', 2, 3)
-    ('e', 3, 4)
-    ('mo', 0, 2)
-    ('or', 1, 3)
-    ('re', 2, 4)
-    ('mor', 0, 3)
-    ('ore', 1, 4)
-    ('more', 0, 4)
-
-    Set *reverse* to ``True`` to yield the same items in the opposite order.
-
-
-    """
-    r = range(1, len(seq) + 1)
-    if reverse:
-        r = reversed(r)
-    return (
-        (seq[i : i + L], i, i + L) for L in r for i in range(len(seq) - L + 1)
-    )
-
-
 class bucket:
     """Wrap *iterable* and return an object that buckets the iterable into
     child iterables based on a *key* function.
@@ -1899,34 +1788,6 @@ def distribute(n, iterable):
     return [islice(it, index, None, n) for index, it in enumerate(children)]
 
 
-def stagger(iterable, offsets=(-1, 0, 1), longest=False, fillvalue=None):
-    """Yield tuples whose elements are offset from *iterable*.
-    The amount by which the `i`-th item in each tuple is offset is given by
-    the `i`-th item in *offsets*.
-
-        >>> list(stagger([0, 1, 2, 3]))
-        [(None, 0, 1), (0, 1, 2), (1, 2, 3)]
-        >>> list(stagger(range(8), offsets=(0, 2, 4)))
-        [(0, 2, 4), (1, 3, 5), (2, 4, 6), (3, 5, 7)]
-
-    By default, the sequence will end when the final element of a tuple is the
-    last item in the iterable. To continue until the first element of a tuple
-    is the last item in the iterable, set *longest* to ``True``::
-
-        >>> list(stagger([0, 1, 2, 3], longest=True))
-        [(None, 0, 1), (0, 1, 2), (1, 2, 3), (2, 3, None), (3, None, None)]
-
-    By default, ``None`` will be used to replace offsets beyond the end of the
-    sequence. Specify *fillvalue* to use some other value.
-
-    """
-    children = tee(iterable, len(offsets))
-
-    return zip_offset(
-        *children, offsets=offsets, longest=longest, fillvalue=fillvalue
-    )
-
-
 def zip_offset(*iterables, offsets, longest=False, fillvalue=None):
     """``zip`` the input *iterables* together, but offset the `i`-th iterable
     by the `i`-th item in *offsets*.
@@ -4232,46 +4093,6 @@ class callback_iter:
         yield from remaining
 
 
-def windowed_complete(iterable, n):
-    """
-    Yield ``(beginning, middle, end)`` tuples, where:
-
-    * Each ``middle`` has *n* items from *iterable*
-    * Each ``beginning`` has the items before the ones in ``middle``
-    * Each ``end`` has the items after the ones in ``middle``
-
-    >>> iterable = range(7)
-    >>> n = 3
-    >>> for beginning, middle, end in windowed_complete(iterable, n):
-    ...     print(beginning, middle, end)
-    () (0, 1, 2) (3, 4, 5, 6)
-    (0,) (1, 2, 3) (4, 5, 6)
-    (0, 1) (2, 3, 4) (5, 6)
-    (0, 1, 2) (3, 4, 5) (6,)
-    (0, 1, 2, 3) (4, 5, 6) ()
-
-    Note that *n* must be at least 0 and most equal to the length of
-    *iterable*.
-
-    This function will exhaust the iterable and may require significant
-    storage.
-    """
-    if n < 0:
-        raise ValueError('n must be >= 0')
-
-    seq = tuple(iterable)
-    size = len(seq)
-
-    if n > size:
-        raise ValueError('n must be <= len(seq)')
-
-    for i in range(size - n + 1):
-        beginning = seq[:i]
-        middle = seq[i : i + n]
-        end = seq[i + n :]
-        yield beginning, middle, end
-
-
 def all_unique(iterable, key=None):
     """
     Returns ``True`` if all the elements of *iterable* are unique (no two
@@ -5665,3 +5486,13 @@ def random_ordered_range(*args):
     n = len(range_object)
     for index in _random_ordered_indices(n):
         yield range_object[index]
+
+
+# Moved to more_itertools.windows; re-exported here for backward compatibility.
+from .windows import (  # noqa: E402
+    stagger,
+    substrings,
+    substrings_indexes,
+    windowed,
+    windowed_complete,
+)
diff --git a/more_itertools/more.pyi b/more_itertools/more.pyi
index ca5cf57..e35cc4b 100644
--- a/more_itertools/more.pyi
+++ b/more_itertools/more.pyi
@@ -242,18 +242,6 @@ def intersperse(
     e: _U, iterable: Iterable[_T], n: int = ...
 ) -> Iterator[_T | _U]: ...
 def unique_to_each(*iterables: Iterable[_T]) -> list[list[_T]]: ...
-@overload
-def windowed(
-    seq: Iterable[_T], n: int, *, step: int = ...
-) -> Iterator[tuple[_T | None, ...]]: ...
-@overload
-def windowed(
-    seq: Iterable[_T], n: int, fillvalue: _U, step: int = ...
-) -> Iterator[tuple[_T | _U, ...]]: ...
-def substrings(iterable: Iterable[_T]) -> Iterator[tuple[_T, ...]]: ...
-def substrings_indexes(
-    seq: Sequence[_T], reverse: bool = ...
-) -> Iterator[tuple[Sequence[_T], int, int]]: ...
 
 class bucket(Generic[_T, _U], Container[_U]):
     def __init__(
@@ -338,32 +326,6 @@ def repeat_last(iterable: Iterable[_T]) -> Iterator[_T]: ...
 @overload
 def repeat_last(iterable: Iterable[_T], default: _U) -> Iterator[_T | _U]: ...
 def distribute(n: int, iterable: Iterable[_T]) -> list[Iterator[_T]]: ...
-@overload
-def stagger(
-    iterable: Iterable[_T],
-    offsets: _SizedIterable[int] = ...,
-    longest: Literal[False] = ...,
-) -> Iterator[tuple[_T, ...]]: ...
-@overload
-def stagger(
-    iterable: Iterable[_T],
-    offsets: _SizedIterable[int] = ...,
-    longest: Literal[False] = ...,
-    fillvalue: object = ...,
-) -> Iterator[tuple[_T, ...]]: ...
-@overload
-def stagger(
-    iterable: Iterable[_T],
-    offsets: _SizedIterable[int] = ...,
-    longest: Literal[True] = ...,
-) -> Iterator[tuple[_T | None, ...]]: ...
-@overload
-def stagger(
-    iterable: Iterable[_T],
-    offsets: _SizedIterable[int] = ...,
-    longest: Literal[True] = ...,
-    fillvalue: _U = ...,
-) -> Iterator[tuple[_T | _U, ...]]: ...
 
 # zip_offset
 @overload
@@ -796,9 +758,6 @@ class callback_iter(Generic[_T_co], Iterator[_T_co]):
     @property
     def result(self) -> Any: ...
 
-def windowed_complete(
-    iterable: Iterable[_T], n: int
-) -> Iterator[tuple[tuple[_T, ...], tuple[_T, ...], tuple[_T, ...]]]: ...
 def all_unique(
     iterable: Iterable[_T], key: Callable[[_T], _U] | None = ...
 ) -> bool: ...
@@ -1020,3 +979,11 @@ def synchronized(
 def random_ordered_range(
     *args: int,
 ) -> Iterator[int]: ...
+
+from .windows import (
+    stagger as stagger,
+    substrings as substrings,
+    substrings_indexes as substrings_indexes,
+    windowed as windowed,
+    windowed_complete as windowed_complete,
+)
diff --git a/more_itertools/windows.py b/more_itertools/windows.py
new file mode 100644
index 0000000..d3657df
--- /dev/null
+++ b/more_itertools/windows.py
@@ -0,0 +1,194 @@
+"""Sliding windows and substrings over iterables."""
+
+from collections import deque
+from itertools import chain, islice, repeat, tee
+from operator import getitem
+
+from .more import zip_offset  # more.py imports this module at its end, after zip_offset
+
+__all__ = [
+    'stagger',
+    'substrings',
+    'substrings_indexes',
+    'windowed',
+    'windowed_complete',
+]
+
+
+def windowed(seq, n, fillvalue=None, step=1):
+    """Return a sliding window of width *n* over the given iterable.
+
+        >>> all_windows = windowed([1, 2, 3, 4, 5], 3)
+        >>> list(all_windows)
+        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
+
+    When the window is larger than the iterable, *fillvalue* is used in place
+    of missing values:
+
+        >>> list(windowed([1, 2, 3], 4))
+        [(1, 2, 3, None)]
+
+    Each window will advance in increments of *step*:
+
+        >>> list(windowed([1, 2, 3, 4, 5, 6], 3, fillvalue='!', step=2))
+        [(1, 2, 3), (3, 4, 5), (5, 6, '!')]
+
+    To slide into the iterable's items, use :func:`chain` to add filler items
+    to the left:
+
+        >>> iterable = [1, 2, 3, 4]
+        >>> n = 3
+        >>> padding = [None] * (n - 1)
+        >>> list(windowed(chain(padding, iterable), 3))
+        [(None, None, 1), (None, 1, 2), (1, 2, 3), (2, 3, 4)]
+    """
+    if n <= 0:
+        raise ValueError('n must be > 0')
+    if step < 1:
+        raise ValueError('step must be >= 1')
+
+    iterator = iter(seq)
+
+    # Generate first window
+    window = deque(islice(iterator, n), maxlen=n)
+
+    # Deal with the first window not being full
+    if not window:
+        return
+    if len(window) < n:
+        yield tuple(window) + ((fillvalue,) * (n - len(window)))
+        return
+    yield tuple(window)
+
+    # Create the filler for the next windows. The padding ensures
+    # we have just enough elements to fill the last window.
+    padding = (fillvalue,) * (n - 1 if step >= n else step - 1)
+    filler = map(window.append, chain(iterator, padding))
+
+    # Generate the rest of the windows
+    for _ in islice(filler, step - 1, None, step):
+        yield tuple(window)
+
+
+def substrings(iterable):
+    """Yield all of the substrings of *iterable*.
+
+        >>> [''.join(s) for s in substrings('more')]
+        ['m', 'o', 'r', 'e', 'mo', 'or', 're', 'mor', 'ore', 'more']
+
+    Note that non-string iterables can also be subdivided.
+
+        >>> list(substrings([0, 1, 2]))
+        [(0,), (1,), (2,), (0, 1), (1, 2), (0, 1, 2)]
+
+    Like subslices() but returns tuples instead of lists
+    and returns the shortest substrings first.
+
+    """
+    seq = tuple(iterable)
+    item_count = len(seq)
+    for n in range(1, item_count + 1):
+        slices = map(slice, range(item_count), range(n, item_count + 1))
+        yield from map(getitem, repeat(seq), slices)
+
+
+def substrings_indexes(seq, reverse=False):
+    """Yield all substrings and their positions in *seq*
+
+    The items yielded will be a tuple of the form ``(substr, i, j)``, where
+    ``substr == seq[i:j]``.
+
+    This function only works for iterables that support slicing, such as
+    ``str`` objects.
+
+    >>> for item in substrings_indexes('more'):
+    ...    print(item)
+    ('m', 0, 1)
+    ('o', 1, 2)
+    ('r', 2, 3)
+    ('e', 3, 4)
+    ('mo', 0, 2)
+    ('or', 1, 3)
+    ('re', 2, 4)
+    ('mor', 0, 3)
+    ('ore', 1, 4)
+    ('more', 0, 4)
+
+    Set *reverse* to ``True`` to yield the same items in the opposite order.
+
+
+    """
+    r = range(1, len(seq) + 1)
+    if reverse:
+        r = reversed(r)
+    return (
+        (seq[i : i + L], i, i + L) for L in r for i in range(len(seq) - L + 1)
+    )
+
+
+def stagger(iterable, offsets=(-1, 0, 1), longest=False, fillvalue=None):
+    """Yield tuples whose elements are offset from *iterable*.
+    The amount by which the `i`-th item in each tuple is offset is given by
+    the `i`-th item in *offsets*.
+
+        >>> list(stagger([0, 1, 2, 3]))
+        [(None, 0, 1), (0, 1, 2), (1, 2, 3)]
+        >>> list(stagger(range(8), offsets=(0, 2, 4)))
+        [(0, 2, 4), (1, 3, 5), (2, 4, 6), (3, 5, 7)]
+
+    By default, the sequence will end when the final element of a tuple is the
+    last item in the iterable. To continue until the first element of a tuple
+    is the last item in the iterable, set *longest* to ``True``::
+
+        >>> list(stagger([0, 1, 2, 3], longest=True))
+        [(None, 0, 1), (0, 1, 2), (1, 2, 3), (2, 3, None), (3, None, None)]
+
+    By default, ``None`` will be used to replace offsets beyond the end of the
+    sequence. Specify *fillvalue* to use some other value.
+
+    """
+    children = tee(iterable, len(offsets))
+
+    return zip_offset(
+        *children, offsets=offsets, longest=longest, fillvalue=fillvalue
+    )
+
+
+def windowed_complete(iterable, n):
+    """
+    Yield ``(beginning, middle, end)`` tuples, where:
+
+    * Each ``middle`` has *n* items from *iterable*
+    * Each ``beginning`` has the items before the ones in ``middle``
+    * Each ``end`` has the items after the ones in ``middle``
+
+    >>> iterable = range(7)
+    >>> n = 3
+    >>> for beginning, middle, end in windowed_complete(iterable, n):
+    ...     print(beginning, middle, end)
+    () (0, 1, 2) (3, 4, 5, 6)
+    (0,) (1, 2, 3) (4, 5, 6)
+    (0, 1) (2, 3, 4) (5, 6)
+    (0, 1, 2) (3, 4, 5) (6,)
+    (0, 1, 2, 3) (4, 5, 6) ()
+
+    Note that *n* must be at least 0 and most equal to the length of
+    *iterable*.
+
+    This function will exhaust the iterable and may require significant
+    storage.
+    """
+    if n < 0:
+        raise ValueError('n must be >= 0')
+
+    seq = tuple(iterable)
+    size = len(seq)
+
+    if n > size:
+        raise ValueError('n must be <= len(seq)')
+
+    for i in range(size - n + 1):
+        beginning = seq[:i]
+        middle = seq[i : i + n]
+        end = seq[i + n :]
+        yield beginning, middle, end
diff --git a/more_itertools/windows.pyi b/more_itertools/windows.pyi
new file mode 100644
index 0000000..ae5f201
--- /dev/null
+++ b/more_itertools/windows.pyi
@@ -0,0 +1,59 @@
+"""Stubs for more_itertools.windows"""
+
+from collections.abc import Iterable, Iterator, Sequence
+from typing import Literal, TypeVar, overload
+
+from _typeshed import Viewable as _SizedIterable
+
+_T = TypeVar('_T')
+_U = TypeVar('_U')
+
+__all__ = [
+    'stagger',
+    'substrings',
+    'substrings_indexes',
+    'windowed',
+    'windowed_complete',
+]
+
+@overload
+def windowed(
+    seq: Iterable[_T], n: int, *, step: int = ...
+) -> Iterator[tuple[_T | None, ...]]: ...
+@overload
+def windowed(
+    seq: Iterable[_T], n: int, fillvalue: _U, step: int = ...
+) -> Iterator[tuple[_T | _U, ...]]: ...
+def substrings(iterable: Iterable[_T]) -> Iterator[tuple[_T, ...]]: ...
+def substrings_indexes(
+    seq: Sequence[_T], reverse: bool = ...
+) -> Iterator[tuple[Sequence[_T], int, int]]: ...
+@overload
+def stagger(
+    iterable: Iterable[_T],
+    offsets: _SizedIterable[int] = ...,
+    longest: Literal[False] = ...,
+) -> Iterator[tuple[_T, ...]]: ...
+@overload
+def stagger(
+    iterable: Iterable[_T],
+    offsets: _SizedIterable[int] = ...,
+    longest: Literal[False] = ...,
+    fillvalue: object = ...,
+) -> Iterator[tuple[_T, ...]]: ...
+@overload
+def stagger(
+    iterable: Iterable[_T],
+    offsets: _SizedIterable[int] = ...,
+    longest: Literal[True] = ...,
+) -> Iterator[tuple[_T | None, ...]]: ...
+@overload
+def stagger(
+    iterable: Iterable[_T],
+    offsets: _SizedIterable[int] = ...,
+    longest: Literal[True] = ...,
+    fillvalue: _U = ...,
+) -> Iterator[tuple[_T | _U, ...]]: ...
+def windowed_complete(
+    iterable: Iterable[_T], n: int
+) -> Iterator[tuple[tuple[_T, ...], tuple[_T, ...], tuple[_T, ...]]]: ...
PATCH
