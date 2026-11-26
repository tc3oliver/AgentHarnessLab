A user reports a crash in Python-Markdown (the repository in `/app`) with the `legacy_attrs`
extension:

    markdown.markdown('# Header {@id=top}\n\n![img{@id=foo}](i.jpg)', extensions=['legacy_attrs'])

raises `NameError`. Legacy attributes written as `{@key=value}` must again be applied, including in the
`alt` text of images (giving `<img alt="img" id="foo" ...>`) and in element text.

Find and fix the cause. Do not modify the existing tests.
