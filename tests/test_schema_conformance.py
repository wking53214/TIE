"""Packages TIE builds must validate against the reconstructed JSON schema.

The schema is a checked-in file. These tests fail if the runtime model drifts
from it, and they check that the schema can actually reject a broken package.
Skipped (visibly, in the -rs summary) when jsonschema is not installed.
"""

import copy
import dataclasses
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from tie import (  # noqa: E402
    build_package,
    create_source,
    segment_source,
    validate_package,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "tie_package.reconstructed.schema.json"


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _package(source, coverage):
    pkg = build_package(package_id="pkg-test", source=source, coverage=coverage)
    return dataclasses.replace(pkg, validation=validate_package(pkg))


def _as_document(pkg):
    return json.loads(pkg.to_json())


def test_fully_inspected_package_validates():
    src = create_source("doc-1", "A short source text.")
    pkg = _package(src, segment_source(src))
    jsonschema.validate(_as_document(pkg), _schema())


def test_package_with_uninspected_ranges_validates():
    text = "x" * 9000
    src = create_source("doc-2", text)
    pkg = _package(src, segment_source(src, max_chars=4000, not_inspected=[(0, 10)]))
    jsonschema.validate(_as_document(pkg), _schema())


def test_package_with_missing_segments_validates():
    src = create_source("doc-3", "abc")
    pkg = _package(src, segment_source(src, max_chars=4000, declared_length=9000))
    jsonschema.validate(_as_document(pkg), _schema())


def test_schema_rejects_a_package_missing_its_id():
    src = create_source("doc-4", "text")
    doc = copy.deepcopy(_as_document(_package(src, segment_source(src))))
    del doc["package_id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, _schema())
