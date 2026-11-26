A user reports a bug in Python-Markdown (the repository in `/app`). With the `meta` and `wikilinks`
extensions, the `wiki_end_url` meta-data value is ignored:

    md = markdown.Markdown(extensions=['meta', 'wikilinks'])
    md.convert('wiki_base_url: http://example.com/\nwiki_end_url:   .html\nwiki_html_class:\n\n'
               'Some text with a [[WikiLink]].')

returns a link to `http://example.com/WikiLink/`, but the expected output is
`'<p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>'`. Meta-data must still
not carry over to the next document converted with the same instance.

Find and fix the cause. Do not modify the existing tests.
