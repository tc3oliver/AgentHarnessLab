The repository in `/app` is tablib. Three things are broken:

- Exporting a dataset to DBF fails.
- Exporting a dataset to a reStructuredText grid table (`dataset.export('rst', force_grid=True)`) raises a
  `TypeError`; the simple table still works.
- Dates and datetimes written to an ODS file come back as empty cells when the file is read again.

Fix the library. Do not modify the existing tests.
