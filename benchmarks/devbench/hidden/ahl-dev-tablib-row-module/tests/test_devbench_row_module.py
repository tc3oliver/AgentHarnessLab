"""Hidden checks for the devbench refactoring task (not part of upstream tablib)."""

import ast
import importlib
from pathlib import Path

import tablib
import tablib.core


def test_row_lives_in_new_module():
    row = importlib.import_module("tablib.row")
    assert row.Row.__module__ == "tablib.row"


def test_old_and_new_import_paths_are_the_same_class():
    row = importlib.import_module("tablib.row")
    assert tablib.core.Row is row.Row
    assert tablib.Row is row.Row


def test_core_no_longer_defines_row():
    tree = ast.parse(Path(tablib.core.__file__).read_text())
    assert "Row" not in {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def test_rows_and_tags_still_work():
    data = tablib.Dataset(headers=["a", "b"])
    data.append((1, 2), tags=["x"])
    data.append((3, 4))
    assert data.filter("x").dict == [{"a": 1, "b": 2}]
    assert isinstance(data._data[0], tablib.Row)
