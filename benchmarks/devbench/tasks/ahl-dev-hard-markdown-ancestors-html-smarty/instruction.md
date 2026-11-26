The repository in `/app` is Python-Markdown. Three things are broken:

- A custom inline processor that declares parent tags it must not be applied inside (such as `a`) is applied
  inside them anyway: with a custom `+text+` processor that excludes `a`, `[+link+](http://test.com)` renders the
  link text as `<strong>link</strong>` instead of leaving `+link+` unchanged.
- Raw inline HTML that contains a backslash, for example `<img src="..\..\foo.png">`, raises a `TypeError`.
  It must be output unchanged inside a paragraph.
- With the `smarty` extension all substitutions disappear: `a -- b` renders as `<p>a  b</p>`; it must render as
  `<p>a &ndash; b</p>`. Quotes, dashes, ellipses and angled quotes are all affected.

Fix the library. Do not modify the existing tests.
