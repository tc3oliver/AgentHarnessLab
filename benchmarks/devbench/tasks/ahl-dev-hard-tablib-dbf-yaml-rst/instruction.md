The repository in `/app` is tablib. Three things are broken:

- Loading a dataset from DBF data fails with an `AttributeError`: setting `dataset.dbf` to the bytes that
  `dataset.dbf` returned does not round-trip.
- YAML handling raises `NameError` where it used to work: `tablib.detect_format('- {age: 90, first_name: John,
  last_name: Adams}')` and loading that text into a `Dataset` should give format `yaml` and one row, but raise instead.
- Exporting a dataset to a reStructuredText grid table (`dataset.export('rst', force_grid=True)`) raises a
  `TypeError`; the simple table still works.

Fix the library. Do not modify the existing tests.
