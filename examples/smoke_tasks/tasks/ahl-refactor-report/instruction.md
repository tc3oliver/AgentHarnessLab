`/app/report.py` does everything inside `main(path)`. Refactor it without changing what the command
`python3 /app/report.py FILE` prints, so that the logic can be imported:

- `parse_line(line)`: returns `None` for a blank line or a `#` comment, otherwise a dict
  `{"name": str, "qty": int, "price": float}` (name stripped of whitespace);
- `summarize(records)`: takes a list of those dicts and returns
  `{"lines": [(name, amount), ...], "total": float}` where `amount = qty * price`;
- `main(path)` must use these two functions.

Importing `report` must have no side effects.
