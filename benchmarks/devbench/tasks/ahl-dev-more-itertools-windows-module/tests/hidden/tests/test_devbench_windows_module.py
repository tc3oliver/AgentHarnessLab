"""Hidden checks for the devbench refactoring task (not part of upstream more-itertools)."""

import ast
import importlib
from pathlib import Path

import more_itertools
import more_itertools.more as more

NAMES = ["windowed", "windowed_complete", "stagger", "substrings", "substrings_indexes"]


def test_functions_live_in_the_new_module():
    windows = importlib.import_module("more_itertools.windows")
    for name in NAMES:
        function = getattr(windows, name)
        assert function.__module__ == "more_itertools.windows", name
        assert name in windows.__all__, name


def test_old_import_paths_still_work():
    windows = importlib.import_module("more_itertools.windows")
    for name in NAMES:
        assert getattr(more_itertools, name) is getattr(windows, name), name
        assert getattr(more, name) is getattr(windows, name), name


def test_star_import_still_exports_them():
    namespace = {}
    exec("from more_itertools import *", namespace)
    for name in NAMES:
        assert name in namespace, name


def test_more_py_no_longer_defines_them():
    tree = ast.parse(Path(more.__file__).read_text())
    defined = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert not defined & set(NAMES)


def test_stubs_moved():
    package = Path(more.__file__).parent
    stub = package / "windows.pyi"
    assert stub.is_file()
    stub_defs = {n.name for n in ast.walk(ast.parse(stub.read_text())) if isinstance(n, ast.FunctionDef)}
    assert set(NAMES) <= stub_defs
    more_defs = {
        n.name
        for n in ast.walk(ast.parse((package / "more.pyi").read_text()))
        if isinstance(n, ast.FunctionDef)
    }
    assert not more_defs & set(NAMES)


def test_behaviour_unchanged():
    from more_itertools.windows import stagger, substrings, substrings_indexes, windowed, windowed_complete

    assert list(windowed([1, 2, 3, 4], 3)) == [(1, 2, 3), (2, 3, 4)]
    assert list(windowed([1, 2, 3], 2, step=2, fillvalue=0)) == [(1, 2), (3, 0)]
    assert list(substrings("ab")) == [("a",), ("b",), ("a", "b")]
    assert list(substrings_indexes("ab"))[0] == ("a", 0, 1)
    assert list(stagger([0, 1, 2])) == [(None, 0, 1), (0, 1, 2)]
    assert list(windowed_complete([1, 2], 1)) == [((), (1,), (2,)), ((1,), (2,), ())]
