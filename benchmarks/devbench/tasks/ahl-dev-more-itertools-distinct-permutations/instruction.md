The repository in `/app` is more-itertools.

`more_itertools.distinct_permutations(iterable, r=None)` must also work for items that are unhashable or
cannot be sorted, for example `list(distinct_permutations([[1], [1], [2]]))` gives the three distinct
orderings. Currently such input raises `UnboundLocalError`. Fix the library. Do not modify the existing
tests.
