"""Output parsing of the devbench verifier (benchmarks/devbench/tools/verify.py, run in task containers)."""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "devbench_verify", Path(__file__).parents[1] / "benchmarks/devbench/tools/verify.py"
)
assert SPEC and SPEC.loader
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


def test_unittest_counts_come_from_the_summary_even_with_interleaved_output():
    text = (
        "test_a (pkg.T.test_a) ... ok\n"
        "test_b (pkg.T.test_b) ... /x.py:1: DeprecationWarning: old\n  warn()\nok\n"
        "test_c (pkg.T.test_c) ... skipped 'n/a'\n"
        "----------------------------------------------------------------------\n"
        "Ran 3 tests in 0.01s\n\nOK (skipped=1)\n"
    )
    passed, missing = verify.unittest_result(text, ["test_b (pkg.T.test_b)", "test_c (pkg.T.test_c)"])
    assert passed == 2
    assert missing == ["test_c (pkg.T.test_c)"]


def test_unittest_failures_are_missing():
    text = (
        "test_a (pkg.T.test_a) ... FAIL\n"
        "======================================================================\n"
        "FAIL: test_a (pkg.T.test_a)\n"
        "Ran 2 tests in 0.01s\n\nFAILED (failures=1)\n"
    )
    assert verify.unittest_result(text, ["test_a (pkg.T.test_a)", "test_z (pkg.T.test_z)"]) == (
        1,
        ["test_a (pkg.T.test_a)", "test_z (pkg.T.test_z)"],
    )


def test_unittest_without_summary_passes_nothing():
    assert verify.unittest_result("Traceback...\n", []) == (0, [])


def test_pytest_ids_ignore_walk_order_numbers():
    text = "PASSED tests/t.py::test_x[given7-a-f.json]\nFAILED tests/t.py::test_y[given9-b-f.json]\n"
    passed, missing = verify.pytest_result(
        text, ["tests/t.py::test_x[given241-a-f.json]", "tests/t.py::test_y[given1-b-f.json]"]
    )
    assert passed == 1
    assert missing == ["tests/t.py::test_y[given1-b-f.json]"]


def test_pytest_a_case_that_also_failed_is_missing():
    text = "PASSED tests/t.py::test_x[given1-a-f.json]\nFAILED tests/t.py::test_x[given2-a-f.json]\n"
    assert verify.pytest_result(text, ["tests/t.py::test_x[given5-a-f.json]"])[1] == [
        "tests/t.py::test_x[given5-a-f.json]"
    ]
