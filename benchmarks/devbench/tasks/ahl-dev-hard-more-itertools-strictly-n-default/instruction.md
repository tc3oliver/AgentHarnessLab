The repository in `/app` is more-itertools.

`list(more_itertools.strictly_n(iter('abcd'), 3))` currently raises `TypeError: 'NoneType' object is not callable`.
It must raise `ValueError` with the message `Too many items in iterable (got at least 4)`.

Fix the library. Do not modify the existing tests.
