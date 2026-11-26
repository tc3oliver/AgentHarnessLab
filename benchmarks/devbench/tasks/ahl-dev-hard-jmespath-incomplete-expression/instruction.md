The repository in `/app` is jmespath.

`jmespath.compile('length(@,')` currently raises a plain `ParseError` with the message `invalid token: Parse error
at column 9, token "" (EOF), for expression: ...`. It must raise `jmespath.exceptions.IncompleteExpressionError`
(a `ParseError` subclass), with the message

    Invalid jmespath expression: Incomplete expression:
    "length(@,"
              ^

Fix the library. Do not modify the existing tests.
