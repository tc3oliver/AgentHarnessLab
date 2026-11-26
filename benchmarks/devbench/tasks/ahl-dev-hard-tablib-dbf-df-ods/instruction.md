The repository in `/app` is tablib. Three things are broken:

- Exporting a dataset to DBF (`dataset.dbf`) fails.
- Exporting a dataset to a pandas DataFrame (`dataset.export('df')`) fails with a `NameError`.
- Reading back a dataset exported to ODS (`dataset.ods`, loaded into a new `Dataset` with `format='ods'`) gives
  the wrong data: the columns are lost and cells come back as empty or as the text `None`. Headers and values
  (`None` as an empty cell) must survive the round trip.

Fix the library. Do not modify the existing tests.
