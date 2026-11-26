The repository in `/app` is Python-Markdown. Three things are broken:

- A setext heading that is directly followed by more text in the same block loses that text:
  `markdown.markdown('Header\n======\nSome text')` returns only `<h1>Header</h1>`; the paragraph `<p>Some text</p>`
  is missing. The same happens with `---` underlines and with several headings in one block.
- Creating a `Markdown` object with the `meta` extension fails with a `TypeError`.
- Removing an entry by name from one of the processor registries (for example the inline processors) does not
  remove it: the registry keeps its length and the processor still runs.

Fix the library. Do not modify the existing tests.
