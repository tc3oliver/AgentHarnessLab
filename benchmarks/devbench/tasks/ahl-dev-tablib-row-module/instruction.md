The repository in `/app` is tablib. Move the `Row` class out of `src/tablib/core.py` into a new module
`src/tablib/row.py`.

Requirements:

- `Row` is defined in `tablib/row.py` (`Row.__module__ == 'tablib.row'`) and no longer in `core.py`.
- `tablib.core.Row` keeps working and is the same class, and `Row` is also exported from the package
  (`from tablib import Row`).
- Behaviour does not change; the whole test suite (`python -m pytest -o addopts= tests`) passes.

Do not modify the existing tests.
