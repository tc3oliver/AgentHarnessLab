Write `/app/flatten.py`, run as `python3 /app/flatten.py IN.json OUT.json`.

It reads a JSON document whose top level is an object and writes a flat JSON object to `OUT.json`:
- nested object keys are joined with `.`;
- list items use their index as the key part (`a.0.b`);
- an empty object or empty list is kept as a value as is (`"k": {}` / `"k": []`);
- scalars (including `null`) are kept as they are;
- an empty top-level object gives `{}`.

Example: `{"a": {"b": 1}, "c": [10, {"d": 2}]}` becomes `{"a.b": 1, "c.0": 10, "c.1.d": 2}`.
