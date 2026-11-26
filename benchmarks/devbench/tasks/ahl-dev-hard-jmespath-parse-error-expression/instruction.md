The repository in `/app` is jmespath.

`jmespath.compile('foo]baz')` raises a `ParseError` whose message ends with `for expression:` followed by a line
`"None"`. The line must show the expression, `"foo]baz"`, as in

    Unexpected token: ]: Parse error at column 3, token "]" (RBRACKET), for expression:
    "foo]baz"
        ^

Fix the library. Do not modify the existing tests.
