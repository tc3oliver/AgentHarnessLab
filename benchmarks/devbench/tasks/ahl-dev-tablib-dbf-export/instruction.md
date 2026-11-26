The repository in `/app` is tablib.

Exporting a `Dataset` to DBF (`dataset.export('dbf')`) and loading the result back
(`tablib.Dataset().load(data, 'dbf')`) must round-trip text columns and numeric columns, including floats.
At the moment the export fails, for example with `TypeError: can't multiply sequence by non-int of type
'tuple'` for a dataset with a float column, and text columns are not declared correctly. Fix the export.
Do not modify the existing tests.
