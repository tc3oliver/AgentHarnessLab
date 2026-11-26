The repository in `/app` is more-itertools. `more_itertools/more.py` has grown too large. Move these
five functions out of it into a new module `more_itertools/windows.py`:

    windowed, windowed_complete, stagger, substrings, substrings_indexes

Requirements:

- The functions are defined in `more_itertools/windows.py` (so `windowed.__module__` is
  `'more_itertools.windows'`), and that module lists all five in its `__all__`.
- `more.py` no longer contains their definitions.
- Existing imports keep working and give the same objects: `from more_itertools import windowed`,
  `from more_itertools.more import windowed`, and `from more_itertools import *`.
- Their type stubs move as well: the stub definitions live in a new `more_itertools/windows.pyi`
  and are removed from `more_itertools/more.pyi`.
- Behaviour does not change; the whole test suite (`python -m pytest tests`) passes.

Do not modify the existing tests.
