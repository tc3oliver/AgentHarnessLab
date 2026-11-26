The repository in `/app` is tablib. Three things are broken:

- Loading a dataset from DBF data fails with an `AttributeError`: setting `dataset.dbf` to the bytes that
  `dataset.dbf` returned does not round-trip.
- YAML handling raises `NameError` where it used to work: `tablib.detect_format('- {age: 90, first_name: John,
  last_name: Adams}')` and loading that text into a `Dataset` should give format `yaml` and one row, but raise instead.
- In the bundled DBF library, converting a Unix timestamp such as `1571515306` or a compact date string such as
  `'20191019'` or `'191019'` to a date raises an error instead of giving `datetime.date(2019, 10, 19)`.

Fix the library. Do not modify the existing tests.
