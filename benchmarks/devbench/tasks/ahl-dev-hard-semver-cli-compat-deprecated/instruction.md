The repository in `/app` is python-semver. Three things are broken:

- The command line tool's `bump` command fails instead of printing the next version: `pysemver bump major 1.2.3`
  should print `2.0.0`.
- `Version(1, 2, 3).is_compatible(other)` with an argument that is not a `Version` (for example `"wrongtype"` or
  a list) no longer raises `TypeError("Expected a Version type but got ...")`.
- A function decorated with `deprecated(remove="Gone in 99.")` warns with "This function will be removed in
  semver 3." instead of the custom text; without `remove` the message contains the word `None`.

Fix the library. Do not modify the existing tests.
