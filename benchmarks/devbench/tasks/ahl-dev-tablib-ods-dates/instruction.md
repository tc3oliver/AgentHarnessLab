The repository in `/app` is tablib.

Exporting a `Dataset` that contains `datetime.date` and `datetime.datetime` values to ODS and loading the
file back must give the same values back: dates as `datetime.date`, timestamps as `datetime.datetime`.
Currently loading an ODS file that contains a plain date fails with
`ValueError: time data '2020-01-02' does not match format '%Y-%m-%dT%H:%M:%S'`. Fix the library. Do not
modify the existing tests.
