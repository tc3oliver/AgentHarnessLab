`/app/durations.py` has `parse_duration(text)` which should convert strings such as `1h30m`, `2d`, `1h 30m 5s`
or `250ms` to a number of seconds (returned as a float). Supported units are `d`, `h`, `m`, `s` and `ms`, in
any order and any number of times; spaces between parts and around the whole string are allowed. Every number
is a non-negative integer written in digits, so decimals such as `1.5h` and signs such as `-1s` are invalid.
An empty or whitespace-only string, a string with an unknown unit, a number without a unit, an invalid number
or any other leftover text must raise `ValueError`.

The current version gets several of these wrong. Fix it.
