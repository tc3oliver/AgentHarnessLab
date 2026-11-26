The repository in `/app` is jmespath.py.

Malformed expressions must raise the library's own errors (`jmespath.exceptions.LexerError` or
`ParseError`) with a readable message. Some of them, for example `jmespath.compile('"foo')` and
`jmespath.compile('@(foo)')`, currently fail with a `TypeError` raised inside the library instead.

Fix the library so that the whole test suite (`python -m pytest tests`) passes. Do not modify, skip or
delete tests or the compliance test data.
