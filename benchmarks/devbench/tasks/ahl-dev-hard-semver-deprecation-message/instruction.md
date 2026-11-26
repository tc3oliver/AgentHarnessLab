The repository in `/app` is python-semver.

A deprecated module-level function such as `semver.bump_major('1.2.3')` currently emits a `DeprecationWarning` with
the message

    Function 'semver.bump_major' is deprecated. This function will be removed in semver 3.

The message must also say since which version the function is deprecated and what to use instead: it must contain
`Deprecated since version 2.10.0.` before the removal sentence and end with
`Use the respective 'semver.Version.bump_major' instead.`

Fix the library. Do not modify the existing tests.
