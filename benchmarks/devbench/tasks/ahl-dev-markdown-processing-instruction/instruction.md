A user reports a rendering bug in Python-Markdown (the repository in `/app`):

    >>> import markdown
    >>> markdown.markdown("`<?php`\n\n<div>\nfoo\n</div>\n")
    '<p><code>&lt;??php</code></p>\n<div>\nfoo\n</div>'
    >>> markdown.markdown("[test nonsense](<?}]*+|&)>).")
    '<p><a href="??}]*+|&amp;)">test nonsense</a>.</p>'

The `?` after `<` is duplicated. The expected results are
`'<p><code>&lt;?php</code></p>\n<div>\nfoo\n</div>'` and
`'<p><a href="?}]*+|&amp;)">test nonsense</a>.</p>'`.

Find and fix the cause in the library. Do not modify the existing tests.
