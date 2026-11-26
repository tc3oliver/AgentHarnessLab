The repository in `/app` is jmespath.py. JMESPath's comparison and truthiness rules differ from Python's
and are currently private helpers inside `jmespath/visitor.py`. Move them into a new module
`jmespath/comparisons.py` as public functions:

- `equals(x, y)`, `is_comparable(x)` and `is_actual_number(x)`, replacing `_equals`, `_is_comparable` and
  `_is_actual_number` (the helper `_is_special_number_case` moves along; you may rename it);
- `is_false(value)` and `is_true(value)`, replacing the methods `TreeInterpreter._is_false` and
  `TreeInterpreter._is_true`.

The old private functions and methods are removed from `visitor.py`, and the interpreter calls the new
functions. Behaviour does not change; the whole test suite (`python -m pytest tests`) passes.

Do not modify the existing tests.
