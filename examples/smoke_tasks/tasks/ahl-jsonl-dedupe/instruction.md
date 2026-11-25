Write `/app/dedupe.py`, run as `python3 /app/dedupe.py IN.jsonl OUT.jsonl`.

`IN.jsonl` has one JSON object per line. Records are identified by their `"id"` field. For each id keep only
the last record seen, but output the records in the order in which their ids first appeared. Write each
record with `json.dumps(record, sort_keys=True)` on its own line. Blank lines, lines that are not valid JSON,
lines that are not JSON objects and records without an `"id"` are skipped. Ids are compared by value and
type (`1`, `1.0`, `true` and `"1"` are four different ids; `null` is a valid id).
