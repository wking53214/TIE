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

from tie import (
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


# --- a package with every part filled in, built the way a real intake builds one -----------------------------------

def _rich_package():
    """HERALD intake evidence (machine and sign-off), an artifact, an identity reference, a relationship and a
    reconstruction, with a routing label. Serialized with the package's own to_json, as a consumer would receive it."""
    from datetime import datetime, timedelta

    from cryptography.hazmat.primitives import serialization

    from tie import (
        Artifact,
        IdentityReference,
        Relationship,
        SourceRef,
        reconstruct_summary,
    )
    from tie.evidence.herald_intake import (
        evidence_from_herald_export,
        export_key_id,
        signoffs_from_herald_export,
    )

    fixture = json.loads((Path(__file__).resolve().parent / "fixtures" / "herald_export_v4.json").read_text())
    export = fixture["export"]
    key = serialization.load_pem_public_key(fixture["public_key_pem"].encode())
    now = datetime.fromisoformat(export["identity"]["signed_at"]) + timedelta(seconds=30)
    source = create_source(export["document"]["source_id"], fixture["text"])
    coverage = segment_source(source)
    evidence = tuple(evidence_from_herald_export(source, export, trusted_keys={export_key_id(key): key}, now=now))
    signoffs = tuple(signoffs_from_herald_export(source, export, trusted_keys={export_key_id(key): key}, now=now))
    ref = SourceRef(source_id=source.source_id, segment_id=coverage.segments[0].segment_id)
    reconstruction = reconstruct_summary(reconstruction_id="rec1", evidence=evidence, provenance=source.provenance)
    return build_package(
        package_id="pkg-rich", source=source, coverage=coverage, evidence=evidence + signoffs,
        artifacts=(Artifact(artifact_id="a1", name="loan-8891", source_refs=(ref,)),),
        identity_references=(IdentityReference(reference_id="r1", identity_key="loan-8891", source_ref=ref),),
        relationships=(Relationship(relationship_id="rel1", subject_id="a1", predicate="mentions",
                                    object_id=evidence[0].evidence_id),),
        reconstruction=reconstruction, routing_signal="knowledge-review")


def test_a_package_with_every_part_filled_in_validates():
    package = _rich_package()
    assert package.evidence and package.artifacts and package.relationships and package.identity_references
    assert package.validation.valid
    jsonschema.validate(_as_document(package), _schema())


def test_a_routing_signal_that_is_not_a_label_still_serializes_to_the_schema_but_fails_validation():
    """The schema only says the signal is text or null; the label rule lives in validate_package, not the schema."""
    package = dataclasses.replace(_rich_package(), routing_signal="run it now")
    jsonschema.validate(_as_document(package), _schema())
    assert "routing_not_execution" in validate_package(package).errors
