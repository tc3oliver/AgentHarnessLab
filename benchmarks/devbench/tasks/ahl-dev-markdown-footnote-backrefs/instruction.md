The repository in `/app` is Python-Markdown.

With the `footnotes` extension, a footnote that is referenced more than once must get one back-reference
link (`&#8617;`) per reference at the end of its entry in the footnote list: the first link points to
`#fnref:<label>`, the second to `#fnref2:<label>`, the third to `#fnref3:<label>`, and so on.

Currently the last back-reference is missing. For example, for a footnote referenced twice only the
`#fnref:<label>` link is rendered, while both references in the text get their ids (`fnref:<label>`
and `fnref2:<label>`).

Fix the library. Do not modify the existing tests.
