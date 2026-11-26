The repository in `/app` is jmespath.

`list(jmespath.lexer.Lexer().tokenize('foo.bar'))` currently reports the `.` token with `start` 3 and `end` 5.
It must be `start` 3 and `end` 4.

Fix the library. Do not modify the existing tests.
