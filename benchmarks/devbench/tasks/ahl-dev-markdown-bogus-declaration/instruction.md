The repository in `/app` is Python-Markdown.

Text that starts like a CDATA section but is not one, such as `<![`, must be kept as text:
`markdown.markdown('<![')` returns `'<p>&lt;![</p>'`, and the same output is expected with the
`md_in_html` extension enabled. Currently the default parser does not handle this input correctly, and with
`md_in_html` the conversion crashes with `NameError`. Fix both code paths. Do not modify the existing
tests.
