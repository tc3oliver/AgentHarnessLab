The repository in `/app` is python-semver.

A function decorated with `semver._deprecated.deprecated(version="2.10.0")` and no `replace`, named `mock_func`,
currently emits a `DeprecationWarning` with the message

    Function 'semver.mock_func' is deprecated. This function will be removed in semver 3.

The message must also say since which version the function is deprecated and what to use instead: it must
contain `Deprecated since version 2.10.0.` before the removal sentence and end with
`Use the respective 'semver.Version.mock_func' instead.`

Fix the library. Do not modify the existing tests.
