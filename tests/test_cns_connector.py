"""Binding TIE outputs to CNS verdicts: the content, its digest, and ``binds``.

These skip where ``cns`` is not installed. CI installs the extra and sets
TIE_REQUIRE_CNS=1, so there they cannot skip. The connector is binding only:
nothing here judges a package.
"""
import dataclasses
import json
import os
from pathlib import Path

import pytest

if os.environ.get("TIE_REQUIRE_CNS") == "1":  # CI: a missing cns is a failure, not a skip
    import cns.gate as gate
else:
    gate = pytest.importorskip("cns.gate")

from tie import (  # noqa: E402
    Artifact, BuildClassification, CoverageStatus, EpistemicStatus, EvidenceRecord,
    IdentityReference, OriginKind, Provenance, Relationship, SourceRef, build_package, create_source,
    evidence_from_statement, reconstruct_summary, segment_source,
)
from tie.cns_connector import (  # noqa: E402
    HANDOFF_SUBJECT, PACKAGE_SUBJECT, binds, handoff_content, handoff_digest, package_content, package_digest,
)
from tie.evidence.herald_intake import evidence_from_herald_export, export_key_id  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402

from tie.models import TIEPackage, TypedHandoff  # noqa: E402

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "herald_export.json").read_text())
TEXT = FIXTURE["text"]
EXPORT = FIXTURE["export"]
_PUB = serialization.load_pem_public_key(FIXTURE["public_key_pem"].encode())
PINNED = {export_key_id(_PUB): _PUB}

TRANSCRIPT = "Ana: We ship on Friday.\nBo: I think the date may slip.\nAna: Then we tell the client."
PLAIN = (str, int, float, bool, type(None))


def make_package(**overrides) -> TIEPackage:
    """A package built by TIE's own functions, with every optional part present."""
    provenance = Provenance(origin=OriginKind.HUMAN, extraction_origin="manual", lineage_id="lin-1", version="1", notes=("n1",))
    source = create_source("src-1", TRANSCRIPT, title="Standup", provenance=provenance)
    coverage = segment_source(source, max_chars=30, not_inspected=[(60, 70)])
    first = evidence_from_statement(
        source, evidence_id="ev-1", statement="Ana says the ship date is Friday.",
        epistemic_status=EpistemicStatus.EXPLICIT, segment_id=coverage.segments[0].segment_id)
    second = evidence_from_statement(
        source, evidence_id="ev-2", statement="Bo thinks the date may slip.",
        epistemic_status=EpistemicStatus.UNKNOWN, segment_id=coverage.segments[1].segment_id)
    first = dataclasses.replace(first, artifact_ids=("art-1",), relationship_ids=("rel-1",), notes=("e-note",))
    ref = SourceRef(source_id="src-1", source_location="line 1", conversation_id="c1", message_id="m1", segment_id="s")
    kwargs = dict(
        package_id="pkg-1", source=source, coverage=coverage, evidence=(first, second),
        artifacts=(Artifact("art-1", "Ship date", artifact_type="date", source_refs=(ref,), provenance=provenance,
                            version="v2", supersedes=("art-0",), identity_uncertain=True, notes=("a-note",)),),
        identity_references=(IdentityReference("id-1", "person:ana", ref, confidence_note="first name only", uncertain=True),),
        relationships=(Relationship("rel-1", "ev-1", "contradicts", "ev-2", EpistemicStatus.CONFLICTED, provenance, ("r-note",)),),
        reconstruction=reconstruct_summary(reconstruction_id="rec-1", evidence=(first, second), provenance=provenance),
        knowledge_views={"b": [1, 2.5, None], "a": {"y": True, "x": ("p", "q")}},
        routing_signal="knowledge-review",
        objective="Hand the date question to review.",
    )
    kwargs.update(overrides)
    return build_package(**kwargs)


def result_for(content_digest, subject, outcome=None):
    return gate.GateResult(
        gate="other.repo.gate", position=gate.GatePosition.OMEGA,
        outcome=outcome or gate.GateOutcome.PASS, reason="r", subject=subject, subject_digest=content_digest)


def walk(value):
    yield value
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


# ------------------------------------------------------------ determinism

def test_the_same_package_built_twice_has_the_same_content_and_digest():
    one, two = make_package(), make_package()
    assert one is not two
    assert package_content(one) == package_content(two)
    assert package_digest(one) == package_digest(two)
    assert handoff_digest(one.typed_handoff) == handoff_digest(two.typed_handoff)


def test_digest_is_a_sha256_hex_and_repeatable():
    package = make_package()
    digest = package_digest(package)
    assert len(digest) == 64 and int(digest, 16) >= 0
    assert digest == package_digest(package)


# ------------------------------------------------------------ what is bound

def test_every_field_of_the_package_and_the_handoff_is_in_the_content():
    package = make_package()
    assert set(package_content(package)) == {f.name for f in dataclasses.fields(TIEPackage)}
    assert set(handoff_content(package.typed_handoff)) == {f.name for f in dataclasses.fields(TypedHandoff)}


def test_the_source_is_bound_by_hash_and_length_not_by_copying_the_transcript():
    source = package_content(make_package())["source"]
    assert "content" not in source
    assert len(source["content_sha256"]) == 64 and source["content_length"] == len(TRANSCRIPT)
    assert TRANSCRIPT not in json.dumps(package_content(make_package()))


def swap(package, **fields):
    return dataclasses.replace(package, **fields)


def in_source(**fields):
    return lambda p: swap(p, source=dataclasses.replace(p.source, **fields))


def in_first(cls_field, **fields):
    def change(p):
        items = list(getattr(p, cls_field))
        items[0] = dataclasses.replace(items[0], **fields)
        return swap(p, **{cls_field: tuple(items)})
    return change


def in_segment(**fields):
    def change(p):
        segments = list(p.coverage.segments)
        segments[1] = dataclasses.replace(segments[1], **fields)
        return swap(p, coverage=dataclasses.replace(p.coverage, segments=tuple(segments)))
    return change


def in_handoff(**fields):
    return lambda p: swap(p, typed_handoff=dataclasses.replace(p.typed_handoff, **fields))


def in_reconstruction(**fields):
    return lambda p: swap(p, reconstruction=dataclasses.replace(p.reconstruction, **fields))


def in_validation(**fields):
    return lambda p: swap(p, validation=dataclasses.replace(p.validation, **fields))


CHANGES = {
    "package_id": lambda p: swap(p, package_id="pkg-2"),
    "source content": in_source(content=TRANSCRIPT + "!"),
    "source content, one character": in_source(content=TRANSCRIPT.replace("Friday", "Fridax")),
    "source id": in_source(source_id="src-2"),
    "source title": in_source(title="Other"),
    "source media type": in_source(media_type="text/markdown"),
    "source provenance origin": in_source(provenance=Provenance(origin=OriginKind.AI)),
    "coverage source id": lambda p: swap(p, coverage=dataclasses.replace(p.coverage, source_id="src-2")),
    "coverage segment dropped": lambda p: swap(p, coverage=dataclasses.replace(p.coverage, segments=p.coverage.segments[:-1])),
    "segment status": in_segment(status=CoverageStatus.MISSING),
    "segment checksum": in_segment(checksum="0" * 64),
    "segment start": in_segment(start_char=1),
    "segment end": in_segment(end_char=1),
    "segment notes": in_segment(notes=("x",)),
    "segment id": in_segment(segment_id="other"),
    "evidence dropped": lambda p: swap(p, evidence=p.evidence[:1]),
    "evidence reordered": lambda p: swap(p, evidence=tuple(reversed(p.evidence))),
    "evidence statement": in_first("evidence", statement="Ana says the ship date is Thursday."),
    "evidence status": in_first("evidence", epistemic_status=EpistemicStatus.INFERRED),
    "evidence id": in_first("evidence", evidence_id="ev-9"),
    "evidence segment": in_first("evidence", segment_id="other"),
    "evidence artifact ids": in_first("evidence", artifact_ids=("art-2",)),
    "evidence relationship ids": in_first("evidence", relationship_ids=()),
    "evidence notes": in_first("evidence", notes=()),
    "evidence source ref": in_first("evidence", source_ref=SourceRef(source_id="src-1", message_id="m9")),
    "evidence provenance": in_first("evidence", provenance=Provenance(origin=OriginKind.HUMAN_ACCEPTED_AI)),
    "artifact dropped": lambda p: swap(p, artifacts=()),
    "artifact name": in_first("artifacts", name="Ship day"),
    "artifact type": in_first("artifacts", artifact_type="deadline"),
    "artifact version": in_first("artifacts", version="v3"),
    "artifact supersedes": in_first("artifacts", supersedes=()),
    "artifact identity uncertain": in_first("artifacts", identity_uncertain=False),
    "artifact source refs": in_first("artifacts", source_refs=()),
    "identity reference dropped": lambda p: swap(p, identity_references=()),
    "identity key": in_first("identity_references", identity_key="person:bo"),
    "identity uncertain": in_first("identity_references", uncertain=False),
    "identity note": in_first("identity_references", confidence_note=None),
    "relationship dropped": lambda p: swap(p, relationships=()),
    "relationship predicate": in_first("relationships", predicate="supports"),
    "relationship status": in_first("relationships", epistemic_status=EpistemicStatus.EXPLICIT),
    "relationship object": in_first("relationships", object_id="ev-1"),
    "reconstruction dropped": lambda p: swap(p, reconstruction=None),
    "reconstruction text": in_reconstruction(text="- changed"),
    "reconstruction evidence ids": in_reconstruction(evidence_ids=("ev-1",)),
    "reconstruction status": in_reconstruction(epistemic_status=EpistemicStatus.UNKNOWN),
    "reconstruction conflict notes": in_reconstruction(conflict_notes=("c",)),
    "validation dropped": lambda p: swap(p, validation=None),
    "validation valid": in_validation(valid=False),
    "validation check": in_validation(checks={"source_present": False}),
    "validation errors": in_validation(errors=("e",)),
    "validation warnings": in_validation(warnings=()),
    "knowledge view value": lambda p: swap(p, knowledge_views={**p.knowledge_views, "b": [1, 2.5, 0]}),
    "knowledge view key": lambda p: swap(p, knowledge_views={**p.knowledge_views, "c": 1}),
    "handoff dropped": lambda p: swap(p, typed_handoff=None),
    "handoff objective": in_handoff(objective="Other"),
    "handoff source id": in_handoff(source_id="src-2"),
    "handoff evidence ids": in_handoff(evidence_ids=("ev-1",)),
    "handoff artifact ids": in_handoff(artifact_ids=()),
    "handoff known uncertainty": in_handoff(known_uncertainty=()),
    "handoff routing signal": in_handoff(routing_signal="other"),
    "handoff provenance": in_handoff(provenance=Provenance(origin=OriginKind.AI)),
    "routing signal": lambda p: swap(p, routing_signal="other"),
    "build classification": lambda p: swap(p, build_classification=BuildClassification.CONFLICTED),
}


@pytest.mark.parametrize("name", list(CHANGES))
def test_the_package_digest_changes_when_any_bound_field_changes(name):
    package = make_package()
    changed = CHANGES[name](package)
    assert changed != package
    assert package_digest(changed) != package_digest(package)


HANDOFF_CHANGES = {
    "objective": dict(objective="Other"),
    "source id": dict(source_id="src-2"),
    "evidence ids": dict(evidence_ids=("ev-1",)),
    "artifact ids": dict(artifact_ids=()),
    "known uncertainty": dict(known_uncertainty=()),
    "routing signal": dict(routing_signal="other"),
    "provenance": dict(provenance=Provenance(origin=OriginKind.AI)),
}


@pytest.mark.parametrize("name", list(HANDOFF_CHANGES))
def test_the_handoff_digest_changes_when_any_bound_field_changes(name):
    handoff = make_package().typed_handoff
    changed = dataclasses.replace(handoff, **HANDOFF_CHANGES[name])
    assert handoff_digest(changed) != handoff_digest(handoff)


def test_an_int_and_an_equal_float_are_different_content():
    package = make_package()
    floated = swap(package, knowledge_views={**package.knowledge_views, "b": [1.0, 2.5, None]})
    assert floated == package   # Python calls these equal; a verdict about one is not about the other
    assert package_digest(floated) != package_digest(package)


def test_every_top_level_field_is_covered_by_a_change_above():
    covered = {f.name for f in dataclasses.fields(TIEPackage)
               if any(CHANGES[n](make_package()).__dict__[f.name] != getattr(make_package(), f.name) for n in CHANGES)}
    assert covered == {f.name for f in dataclasses.fields(TIEPackage)}


# ------------------------------------------------------------ what is not bound

def test_dict_order_and_tuple_versus_list_in_knowledge_views_do_not_change_the_digest():
    package = make_package()
    reordered = swap(package, knowledge_views={"a": {"x": ["p", "q"], "y": True}, "b": (1, 2.5, None)})
    assert package_digest(reordered) == package_digest(package)
    assert package_content(reordered) == package_content(package)


def test_the_order_of_a_set_in_knowledge_views_does_not_change_the_digest():
    first, second = set([1, 9, 17]), set([17, 9, 1])
    assert list(first) != list(second), "precondition: these sets iterate in different orders"
    one = make_package(knowledge_views={"s": first})
    other = make_package(knowledge_views={"s": second})
    assert package_digest(one) == package_digest(other)
    assert package_content(one)["knowledge_views"]["s"] == [1, 9, 17]


def test_a_set_of_mixed_kinds_still_has_one_order():
    first, second = frozenset([1, 9, (3,)]), frozenset([9, 1, (3,)])   # an int and a tuple cannot be compared
    assert list(first) != list(second), "precondition: these sets iterate in different orders"
    one = make_package(knowledge_views={"s": first})
    other = make_package(knowledge_views={"s": second})
    assert package_digest(one) == package_digest(other)


def test_derived_properties_of_the_coverage_are_not_separate_state():
    package = make_package()
    assert "inspected_segments" not in package_content(package)["coverage"]
    assert "complete" not in package_content(package)["coverage"]


# ------------------------------------------------------------ types

@pytest.mark.parametrize("bad", [None, "package", {"package_id": "x"}, 7, [make_package()]])
def test_a_package_function_rejects_anything_that_is_not_a_package(bad):
    for function in (package_content, package_digest):
        with pytest.raises(TypeError):
            function(bad)


@pytest.mark.parametrize("bad", [None, "handoff", {"objective": "x"}, make_package()])
def test_a_handoff_function_rejects_anything_that_is_not_a_handoff(bad):
    for function in (handoff_content, handoff_digest):
        with pytest.raises(TypeError):
            function(bad)


@pytest.mark.parametrize("bad", [None, "x", {"a": 1}, make_package().evidence[0]])
def test_binds_rejects_anything_that_is_neither_a_package_nor_a_handoff(bad):
    result = result_for("0" * 64, PACKAGE_SUBJECT)
    with pytest.raises(TypeError):
        binds(result, bad)


@pytest.mark.parametrize("views", [
    {"o": object()}, {"n": float("nan")}, {"i": float("inf")}, {1: "int key"}, {"b": b"bytes"}, {"f": lambda: 0},
    {"nested": {"deep": [1, {"bad": object()}]}}])
def test_content_cns_could_not_accept_is_a_type_error(views):
    with pytest.raises(TypeError):
        package_content(make_package(knowledge_views=views))


def test_the_content_only_has_types_cns_accepts():
    package = make_package()
    for content in (package_content(package), handoff_content(package.typed_handoff)):
        assert isinstance(content, dict)
        for node in walk(content):
            assert type(node) in (*PLAIN, list, dict), type(node)
            if isinstance(node, dict):
                assert all(type(k) is str for k in node)
        assert gate.subject_digest(content)  # cns itself accepts it


# ------------------------------------------------------------ binds

def test_binds_is_true_for_the_package_it_was_issued_against():
    package = make_package()
    result = result_for(package_digest(package), PACKAGE_SUBJECT)
    assert result.bound() and binds(result, package)


def test_binds_is_true_for_a_rebuilt_identical_package_and_false_for_a_different_one():
    package = make_package()
    result = result_for(package_digest(package), PACKAGE_SUBJECT)
    assert binds(result, make_package())
    assert not binds(result, make_package(package_id="pkg-2"))
    assert not binds(result, CHANGES["evidence statement"](package))
    assert not binds(result, CHANGES["segment status"](package))


def test_binds_is_true_for_the_handoff_it_was_issued_against_and_false_for_another():
    handoff = make_package().typed_handoff
    result = result_for(handoff_digest(handoff), HANDOFF_SUBJECT)
    assert binds(result, handoff)
    assert not binds(result, dataclasses.replace(handoff, routing_signal="other"))


@pytest.mark.parametrize("kwargs", [
    dict(),
    dict(subject=""),
    dict(subject="tie.other"),
])
def test_binds_checks_the_subject_label(kwargs):
    package = make_package()
    wrong = result_for(package_digest(package), "something.else")
    assert not binds(wrong, package, **kwargs)
    assert binds(wrong, package, subject="something.else")


def test_binds_uses_the_subject_it_is_given_and_not_the_default_one():
    package = make_package()
    labelled = result_for(package_digest(package), "custom.label")
    assert binds(labelled, package, subject="custom.label")
    assert not binds(labelled, package)
    assert not binds(result_for(package_digest(package), PACKAGE_SUBJECT), package, subject="custom.label")


def test_a_package_verdict_does_not_bind_to_its_handoff_and_back():
    package = make_package()
    on_package = result_for(package_digest(package), PACKAGE_SUBJECT)
    on_handoff = result_for(handoff_digest(package.typed_handoff), HANDOFF_SUBJECT)
    assert not binds(on_package, package.typed_handoff)
    assert not binds(on_handoff, package)
    # even with the right digest, the label keeps the two apart
    assert not binds(result_for(handoff_digest(package.typed_handoff), PACKAGE_SUBJECT), package.typed_handoff)


def test_an_unbound_or_hand_built_result_binds_to_nothing():
    package = make_package()
    bare = gate.GateResult(gate="g", position=gate.GatePosition.ALPHA, outcome=gate.GateOutcome.PASS)
    assert not bare.bound() and not binds(bare, package)
    no_digest = gate.GateResult(gate="g", position=gate.GatePosition.ALPHA, outcome=gate.GateOutcome.PASS, subject=PACKAGE_SUBJECT)
    assert not binds(no_digest, package)
    no_subject = gate.GateResult(gate="g", position=gate.GatePosition.ALPHA, outcome=gate.GateOutcome.PASS,
                                 subject_digest=package_digest(package))
    assert not binds(no_subject, package)
    assert not binds(bare, package, subject="")


@pytest.mark.parametrize("impostor", [None, "pass", {"subject": PACKAGE_SUBJECT}, object()])
def test_something_that_is_not_a_gate_result_binds_to_nothing(impostor):
    assert binds(impostor, make_package()) is False


def test_an_impostor_that_claims_to_bind_is_not_believed():
    class Liar:
        def binds(self, subject, digest):
            return True

    assert binds(Liar(), make_package()) is False


@pytest.mark.parametrize("outcome", list(gate.GateOutcome))
def test_binding_does_not_depend_on_the_verdict(outcome):
    package = make_package()
    assert binds(result_for(package_digest(package), PACKAGE_SUBJECT, outcome), package)


# ------------------------------------------------------------ against TIE's own pipeline

def test_a_package_built_by_the_real_pipeline_from_a_herald_export_binds():
    source = create_source("inv-1", TEXT, provenance=Provenance(origin=OriginKind.HUMAN))
    coverage = segment_source(source, max_chars=40)
    evidence = tuple(evidence_from_herald_export(source, EXPORT, trusted_keys=PINNED))
    assert evidence and all(isinstance(e, EvidenceRecord) for e in evidence)
    reconstruction = reconstruct_summary(reconstruction_id="r-1", evidence=evidence, provenance=source.provenance)
    package = build_package(package_id="pkg-inv", source=source, coverage=coverage, evidence=evidence,
                            reconstruction=reconstruction, routing_signal="knowledge-review")
    assert package.validation.valid

    result = result_for(package_digest(package), PACKAGE_SUBJECT)
    assert binds(result, package)
    again = build_package(package_id="pkg-inv", source=source, coverage=coverage, evidence=evidence,
                          reconstruction=reconstruction, routing_signal="knowledge-review")
    assert binds(result, again)
    assert binds(result_for(handoff_digest(package.typed_handoff), HANDOFF_SUBJECT), again.typed_handoff)

    other_source = create_source("inv-1", TEXT.replace("1250", "1350"), provenance=source.provenance)
    other = build_package(package_id="pkg-inv", source=other_source, coverage=segment_source(other_source, max_chars=40),
                          evidence=evidence, reconstruction=reconstruction, routing_signal="knowledge-review")
    assert not binds(result, other)


def test_a_package_that_says_part_of_the_source_was_not_read_does_not_bind_to_one_that_says_all_was():
    source = create_source("s", "x" * 100)
    read_all = build_package(package_id="p", source=source, coverage=segment_source(source, max_chars=40))
    skipped = build_package(package_id="p", source=source, coverage=segment_source(source, max_chars=40, not_inspected=[(0, 10)]))
    assert package_digest(read_all) != package_digest(skipped)
    assert not binds(result_for(package_digest(read_all), PACKAGE_SUBJECT), skipped)


def test_a_truncated_copy_does_not_bind_to_the_whole():
    source = create_source("s", "x" * 100)
    whole = build_package(package_id="p", source=source, coverage=segment_source(source, max_chars=40))
    truncated = build_package(package_id="p", source=source, coverage=segment_source(source, max_chars=40, declared_length=250))
    assert not binds(result_for(package_digest(whole), PACKAGE_SUBJECT), truncated)
    assert any(s.status is CoverageStatus.MISSING for s in truncated.coverage.segments)
