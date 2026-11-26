The repository in `/app` is more-itertools.

`more_itertools.gray_product(*iterables)` yields the Cartesian product in Gray-code order, where only one
element changes between consecutive tuples:

    list(gray_product(('a', 'b', 'c'), range(1, 3)))
    == [('a', 1), ('b', 1), ('c', 1), ('c', 2), ('b', 2), ('a', 2)]

It currently fails with `IndexError` (for example `list(gray_product('ab', [1, 2]))`). Fix the library so
that it yields every combination exactly once in that order. Do not modify the existing tests.
