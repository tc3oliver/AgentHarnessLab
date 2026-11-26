The repository in `/app` is more-itertools.

`more_itertools.bucket(iterable, key, validator=None)` is called with a validator, for example:

    D = bucket([10, 20, 30, 11, 21, 31, 12, 22, 23, 33], key=lambda x: 10 * (x // 10), validator=lambda x: x != 20)
    set(D)

Currently `set(D)` is `set()`. It must be `{10, 30}`.

Fix the library. Do not modify the existing tests.
