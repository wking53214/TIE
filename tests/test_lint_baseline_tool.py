"""The baseline checker fails on new findings and never on existing ones; it hides nothing."""

import importlib.util
import json
from collections import Counter
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "tools" / "lint_baseline.py"
_SPEC = importlib.util.spec_from_file_location("lint_baseline", _PATH)
tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tool)


def test_a_count_equal_to_the_baseline_passes():
    failures, improvements = tool.compare(Counter({"a.py::F401": 2}), {"a.py::F401": 2})
    assert failures == [] and improvements == []


def test_a_count_above_the_baseline_fails():
    failures, _ = tool.compare(Counter({"a.py::F401": 3}), {"a.py::F401": 2})
    assert failures and "baseline allows 2" in failures[0]


def test_a_new_file_or_rule_fails():
    failures, _ = tool.compare(Counter({"b.py::F401": 1, "a.py::E501": 1}), {"a.py::F401": 1})
    assert len(failures) == 2


def test_a_count_below_the_baseline_passes_and_says_to_tighten():
    failures, improvements = tool.compare(Counter({"a.py::F401": 1}), {"a.py::F401": 2})
    assert failures == [] and "tighten" in improvements[0]


def test_a_finding_that_disappeared_entirely_is_reported_as_an_improvement():
    failures, improvements = tool.compare(Counter(), {"a.py::F401": 2})
    assert failures == [] and improvements


def test_ruff_output_is_grouped_by_file_and_rule():
    root = tool.ROOT
    raw = json.dumps([{"filename": str(root / "src" / "x.py"), "code": "F401"},
                      {"filename": str(root / "src" / "x.py"), "code": "F401"},
                      {"filename": str(root / "src" / "y.py"), "code": "I001"}])
    assert tool.ruff_counts(raw) == Counter({"src/x.py::F401": 2, "src/y.py::I001": 1})


def test_mypy_output_is_grouped_by_file_and_error_code():
    text = ("src/x.py:3: error: bad thing  [arg-type]\nsrc/x.py:9: error: again  [arg-type]\n"
            "src/x.py:9: note: ignore me\nFound 2 errors in 1 file (checked 1 source file)\n")
    assert tool.mypy_counts(text) == Counter({"src/x.py::arg-type": 2})


def test_the_committed_baseline_has_both_tools_and_positive_counts():
    data = json.loads(tool.BASELINE.read_text())
    assert set(data) == {"ruff", "mypy"}
    assert all(isinstance(n, int) and n > 0 for tool_counts in data.values() for n in tool_counts.values())
