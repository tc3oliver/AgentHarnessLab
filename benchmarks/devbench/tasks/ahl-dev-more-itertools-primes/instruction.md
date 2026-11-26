The repository in `/app` is more-itertools. Two prime-number helpers are broken:

- `more_itertools.sieve(n)` must yield all primes less than `n`; `list(sieve(30))` is
  `[2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`, but it currently yields only `[2]`.
- `more_itertools.nth_prime(n)` must return the n-th prime counting from 0 (`nth_prime(0) == 2`,
  `nth_prime(100) == 547`); it currently returns wrong results such as `None`.

Fix both. Do not modify the existing tests.
