Write an executable bash script `/app/merge_env.sh`, used as `/app/merge_env.sh FILE...`.

Each file contains `KEY=VALUE` lines. Merge them in argument order, so a later file overrides an earlier one.
Print the result to stdout as `KEY=VALUE` lines sorted by key (plain byte order). Rules:
- blank lines and lines whose first non-blank character is `#` are ignored;
- an optional leading `export ` is removed;
- split on the first `=` only, so values may contain `=`;
- keep the value exactly as written (spaces and quotes included), but leading and trailing whitespace
  around the key is removed;
- lines without `=` are ignored.

Exit with status 1 and a message on stderr if any file is missing; print nothing to stdout in that case.
With no arguments print nothing.
