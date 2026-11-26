The repository in `/app` is tablib.

`Dataset.export('sql')` writes one `INSERT` statement per row, each on its own line, and the output ends
with a newline. With `commit=True` a final `COMMIT;` line follows:

    'INSERT INTO export_table (a,b) VALUES (1, 2);\nCOMMIT;\n'

Currently the newline after the last `INSERT` is missing, so the output is
`'INSERT INTO export_table (a,b) VALUES (1, 2);COMMIT;\n'`. Fix the library. Do not modify the existing
tests.
