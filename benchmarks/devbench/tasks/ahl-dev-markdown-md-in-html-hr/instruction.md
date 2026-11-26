A user reports a bug in Python-Markdown (the repository in `/app`) with the `md_in_html` extension.
A self-closing tag with a `markdown` attribute is copied into the output unchanged:

    markdown.markdown('*e1*\n<hr markdown="1" />\n*e2*', extensions=['md_in_html'])

returns `'<p><em>e1</em></p>\n<hr markdown="1" />\n<p><em>e2</em></p>'`, but the expected output is
`'<p><em>e1</em></p>\n<hr>\n<p><em>e2</em></p>'`: the `markdown` attribute is consumed like on other
elements.

Find and fix the cause. Do not modify the existing tests.
