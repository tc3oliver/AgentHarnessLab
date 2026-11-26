A user reports a bug in jmespath.py (the repository in `/app`):

    >>> jmespath.search('max(@)', [1, 'a', 3])
    TypeError: '>' not supported between instances of 'str' and 'int'

Functions that take an array of numbers or an array of strings (`max`, `min`, `sort`, and others) must
reject arrays that mix element types with `jmespath.exceptions.JMESPathTypeError`, as the JMESPath
specification requires, instead of leaking a Python `TypeError`.

Find and fix the cause. Do not modify the existing tests or the compliance test data.
