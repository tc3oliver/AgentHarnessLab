The repository in `/app` is python-semver. Two problems were reported:

1. `Version.match(expr)` (and the module-level `semver.match`) must raise `ValueError` for a malformed
   expression such as `'!'`, `''` or `'?1.0.0'`; it currently raises `TypeError` for some of them.
2. The command-line interface (`python -m semver ...` / `semver.cli.main([...])`) must print the result
   of commands such as `bump`, `compare` and `nextver` to standard output, for example `nextver 1.2.3 minor`
   prints `1.3.0`. Currently nothing is printed.

Fix both. Do not modify the existing tests.
