The repository in `/app` is Python-Markdown. Move the `Registry` class and its helper `_PriorityItem`
out of `markdown/util.py` into a new module `markdown/registry.py`.

Requirements:

- Both are defined in `markdown/registry.py` (their `__module__` is `'markdown.registry'`) and no longer
  defined in `markdown/util.py`.
- `markdown.util.Registry` and `markdown.util._PriorityItem` remain importable for third-party
  extensions and are the same objects as the new ones.
- Code inside the `markdown` package (including the bundled extensions) no longer refers to
  `util.Registry` or imports `Registry` from `util`; it uses the new module.
- Behaviour does not change; the whole test suite (`python -m unittest discover tests`) passes.

Do not modify the existing tests.
