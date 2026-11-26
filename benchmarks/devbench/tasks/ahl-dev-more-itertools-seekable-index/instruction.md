The repository in `/app` is more-itertools.

Indexing a `peekable` or `seekable` iterator must look ahead without consuming items: for
`p = more_itertools.seekable('abcdef')`, `p[2]` is `'c'`, and `next(p)` afterwards is still `'a'`. The same
holds for `peekable`, including after `prepend()`.

At the moment indexing further ahead than the items already cached raises `IndexError` (for example
`seekable('abcdef')[2]` on a fresh iterator). Fix the library. Do not modify the existing tests.
