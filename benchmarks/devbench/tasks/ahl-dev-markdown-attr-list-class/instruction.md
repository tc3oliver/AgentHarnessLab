A user reports a bug in Python-Markdown (the repository in `/app`) when setting CSS classes with
attribute lists:

    >>> import markdown
    >>> markdown.markdown("# Title {.big}", extensions=["attr_list"])
    '<h1 class="None big">Title</h1>'

The expected result is `'<h1 class="big">Title</h1>'`. Several classes, as in `{.a .b}`, must all be
kept, giving `class="a b"`. The same applies to inline elements and table cells.

Find and fix the cause in the library. Do not modify the existing tests.
