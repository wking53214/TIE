"""Routing is data, never authorization. validate_package checks the data shape and consistency; nothing acts on it."""

import dataclasses
import re
from pathlib import Path

import pytest

from tie import build_package, create_source, segment_source
from tie.validation.validate import (
    ROUTING_LABEL,
    routing_is_data_only,
    validate_package,
)


def _package(routing_signal=None):
    source = create_source("s", "Some text.")
    return build_package(package_id="p", source=source, coverage=segment_source(source), routing_signal=routing_signal)


@pytest.mark.parametrize("label", [None, "review", "knowledge-review", "other", "Gem.Review_2", "a" * 64])
def test_a_label_or_no_signal_is_valid_routing(label):
    package = _package(label)
    assert package.validation.checks["routing_not_execution"] is True
    assert package.validation.valid


@pytest.mark.parametrize("signal", [
    "run the deployment now",            # a sentence: spaces
    "execute; rm -rf /",                 # command syntax
    "review\nexecute",                   # a second line
    "review ",                           # trailing space
    "",                                  # empty is not a label (None means no signal)
    "9review",                           # must start with a letter
    "a" * 65,                            # too long to be a label
    "review/../../etc",                  # path syntax
    "$(whoami)",
])
def test_a_signal_that_is_not_a_label_fails_validation(signal):
    package = _package(signal)
    assert package.validation.checks["routing_not_execution"] is False
    assert "routing_not_execution" in package.validation.errors
    assert not package.validation.valid


def test_a_non_text_signal_fails_validation():
    package = dataclasses.replace(_package("review"), routing_signal=5)
    assert not routing_is_data_only(package)


def test_a_package_and_handoff_that_disagree_fail_validation():
    package = _package("review")
    contradictory = dataclasses.replace(
        package, typed_handoff=dataclasses.replace(package.typed_handoff, routing_signal="publish"))
    assert not routing_is_data_only(contradictory)
    result = validate_package(contradictory)
    assert "routing_not_execution" in result.errors and not result.valid


def test_a_handoff_signal_the_package_lacks_fails_validation():
    package = _package(None)
    contradictory = dataclasses.replace(
        package, typed_handoff=dataclasses.replace(package.typed_handoff, routing_signal="review"))
    assert not routing_is_data_only(contradictory)


def test_the_label_shape_is_exactly_what_is_documented():
    assert ROUTING_LABEL.pattern == r"[A-Za-z][A-Za-z0-9._-]{0,63}"


def test_a_valid_label_is_still_only_data():
    """Passing validation is not permission: the package carries no field that grants or records execution."""
    package = _package("review")
    names = {f.name for f in dataclasses.fields(package)} | {f.name for f in dataclasses.fields(package.typed_handoff)}
    assert not any(re.search(r"authori[sz]|permit|approv|execute|run_", n) for n in names)


def test_no_tie_module_reads_the_routing_signal_to_act_on_it():
    """Only the model, the builder and validation mention the signal (validation only checks its shape); a new reader must come here on purpose."""
    root = Path(__file__).resolve().parents[2] / "src" / "tie"
    mentions = {str(p.relative_to(root)) for p in root.rglob("*.py") if "routing_signal" in p.read_text()}
    assert mentions == {"models/core.py", "package/builder.py", "validation/validate.py"}
