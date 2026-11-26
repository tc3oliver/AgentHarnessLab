"""Hidden checks for the devbench refactoring task (not part of upstream Python-Markdown)."""

import ast
import importlib
import unittest
from pathlib import Path

import markdown
import markdown.util


def _code_mentions_util_registry(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "Registry":
            if isinstance(node.value, ast.Name) and node.value.id == "util":
                hits.append(f"{path.name}:{node.lineno}")
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[-1] == "util":
            if any(alias.name in ("Registry", "_PriorityItem") for alias in node.names):
                hits.append(f"{path.name}:{node.lineno}")
    return hits


class TestRegistryModule(unittest.TestCase):
    def test_registry_lives_in_new_module(self):
        registry = importlib.import_module("markdown.registry")
        self.assertEqual(registry.Registry.__module__, "markdown.registry")
        self.assertEqual(registry._PriorityItem.__module__, "markdown.registry")

    def test_util_keeps_backward_compatible_names(self):
        registry = importlib.import_module("markdown.registry")
        self.assertIs(markdown.util.Registry, registry.Registry)
        self.assertIs(markdown.util._PriorityItem, registry._PriorityItem)

    def test_util_no_longer_defines_it(self):
        tree = ast.parse(Path(markdown.util.__file__).read_text(encoding="utf-8"))
        classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        self.assertFalse(classes & {"Registry", "_PriorityItem"})

    def test_package_code_imports_from_new_module(self):
        package = Path(markdown.__file__).parent
        hits = []
        for path in sorted(package.rglob("*.py")):
            if path.name != "util.py":
                hits += _code_mentions_util_registry(path)
        self.assertEqual(hits, [])

    def test_processors_use_the_registry(self):
        registry = importlib.import_module("markdown.registry")
        md = markdown.Markdown(extensions=["smarty"])
        for collection in (
            md.preprocessors,
            md.inlinePatterns,
            md.treeprocessors,
            md.postprocessors,
            md.parser.blockprocessors,
        ):
            self.assertIsInstance(collection, registry.Registry)
        self.assertEqual(md.convert("*a* -- b"), "<p><em>a</em> &ndash; b</p>")


if __name__ == "__main__":
    unittest.main()
