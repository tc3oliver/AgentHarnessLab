Write `/app/aggregate.py`, run as `python3 /app/aggregate.py IN.csv OUT.csv`.

`IN.csv` has a header row and at least the columns `region` and `amount` (other columns may exist and
the column order may vary). Fields can be quoted and may contain commas. Sum `amount` per `region`.
Surrounding whitespace in `amount` is ignored. Rows whose `amount` is empty or is not a finite decimal
number (for example `abc`, `nan`, `inf`) are ignored; negative amounts are valid.

`OUT.csv` must have the header `region,total`, one row per region, sorted by total descending and then
by region ascending. Totals are written with exactly two decimals (for example `12.50`).
Use exact decimal arithmetic, not binary floats: sum the exact values first and round only the final total,
to two decimals, rounding half to even (so a total of `1.005` is written as `1.00` and `0.015` as `0.02`).
