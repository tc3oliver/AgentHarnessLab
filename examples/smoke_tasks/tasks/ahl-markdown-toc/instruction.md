Write `/app/gen_toc.py`, run as `python3 /app/gen_toc.py FILE.md`. It prints a table of contents for the
Markdown file to stdout, one line per heading of level 1 to 3 (`#`, `##`, `###` followed by a space):

`<indent>- [<title>](#<anchor>)` where `<indent>` is `2 * (level - 1)` spaces (so `#` has none, `##` has 2,
`###` has 4).

The anchor is the title lowercased, with every character removed that is not an ASCII letter, digit, space or
hyphen, then spaces replaced by hyphens. If the same anchor appeared before, append `-1`, `-2`, and so on
for later duplicates. Headings inside fenced code blocks (lines starting with three backticks toggle the
fence) are ignored, and so are headings deeper than level 3. Trailing `#` characters and spaces in a
heading are not part of the title.
