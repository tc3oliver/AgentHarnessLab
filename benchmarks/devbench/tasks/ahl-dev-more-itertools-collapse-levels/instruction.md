The repository in `/app` is more-itertools.

`more_itertools.collapse(iterable, base_type=None, levels=None)` flattens nested iterables. With
`levels=n` it must flatten only the first `n` levels of nesting and keep anything deeper as it is:

    list(collapse([[1], 2, [[3], 4], [[[5]]]], levels=2)) == [1, 2, 3, 4, [5]]

and `collapse(x, levels=1)` must give the same items as `flatten(x)`. At the moment the level limit is
not respected when `levels` is given.

Fix the library. Do not modify the existing tests.
