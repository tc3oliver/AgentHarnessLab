"""Hidden checks for the devbench refactoring task (not part of upstream jmespath.py)."""

import ast
import importlib
from pathlib import Path

import jmespath
import jmespath.visitor as visitor
import pytest

PUBLIC = ["equals", "is_comparable", "is_actual_number", "is_false", "is_true"]
OLD = ["_equals", "_is_special_number_case", "_is_comparable", "_is_actual_number"]


def test_helpers_are_public_functions_of_the_new_module():
    comparisons = importlib.import_module("jmespath.comparisons")
    for name in PUBLIC:
        assert getattr(comparisons, name).__module__ == "jmespath.comparisons", name


def test_visitor_no_longer_defines_them():
    tree = ast.parse(Path(visitor.__file__).read_text())
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert not defined & {*OLD, "_is_false", "_is_true"}


def test_interpreter_uses_the_new_module(monkeypatch):
    comparisons = importlib.import_module("jmespath.comparisons")
    calls = []
    original = comparisons.is_false

    def spy(value):
        calls.append(value)
        return original(value)

    monkeypatch.setattr(comparisons, "is_false", spy)
    monkeypatch.setattr(visitor, "is_false", spy, raising=False)
    assert jmespath.search("a || b", {"a": [], "b": 2}) == 2
    assert calls


@pytest.mark.parametrize(
    ("value", "expected"),
    [("", True), ([], True), ({}, True), (None, True), (False, True), (0, False), ("a", False), ([0], False)],
)
def test_is_false(value, expected):
    comparisons = importlib.import_module("jmespath.comparisons")
    assert comparisons.is_false(value) is expected
    assert comparisons.is_true(value) is (not expected)


def test_equality_rules():
    comparisons = importlib.import_module("jmespath.comparisons")
    assert comparisons.equals(1, 1.0)
    assert not comparisons.equals(1, True)
    assert not comparisons.equals(False, 0)
    assert comparisons.is_comparable("x") and comparisons.is_comparable(2.5)
    assert not comparisons.is_comparable(True) and not comparisons.is_actual_number(False)
