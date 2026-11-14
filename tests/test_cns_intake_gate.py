"""The intake gate: whether a HERALD export, offered with a source, is taken in as TIE evidence.

TIE judges nothing about content. This gate answers one question about integrity, the one `evidence_from_herald_export`
already answers by raising: did the export verify against a pinned HERALD key, and was every admitted claim read from this
very text. PASS carries the evidence ids TIE produced, bound to the source, so a decision can say which records came from
this document; anything else is a TERMINAL_BREACH. Skipped where ``cns`` is absent, like the rest of the connected half.
"""
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization

from tie.evidence.herald_intake import evidence_from_herald_export
from tie.source.loader import create_source

if os.environ.get("TIE_REQUIRE_CNS") == "1":  # CI: a missing cns is a failure, not a skip
    import cns.gate as gate
else:
    gate = pytest.importorskip("cns.gate")

from tie.cns_connector import (  # noqa: E402
    GATE_NAME, INTAKE_SUBJECT, HeraldIntake, TieIntakeGate, intake_content, intake_digest,
)
from tie.evidence.herald_intake import export_key_id  # noqa: E402

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "herald_export.json").read_text())
TEXT, EXPORT = FIXTURE["text"], FIXTURE["export"]
_PUB = serialization.load_pem_public_key(FIXTURE["public_key_pem"].encode())
TRUSTED = {export_key_id(_PUB): _PUB}


def intake(text=TEXT, export=None, source_id="inv-1"):
    return HeraldIntake(create_source(source_id, text), EXPORT if export is None else export)


def check(candidate, trusted=None):
    return TieIntakeGate(TRUSTED if trusted is None else trusted).check(candidate)


def test_the_gate_stands_at_alpha_and_has_a_stable_name():
    g = TieIntakeGate(TRUSTED)
    assert g.name == GATE_NAME == "tie_intake" and g.position is gate.GatePosition.ALPHA


def test_a_verified_export_for_its_own_text_passes_bound_to_the_source_and_the_evidence_tie_produced():
    candidate = intake()
    result = check(candidate)
    assert result.outcome is gate.GateOutcome.PASS
    assert result.binds(INTAKE_SUBJECT, intake_digest(candidate.source, evidence_from_herald_export(
        candidate.source, EXPORT, trusted_keys=TRUSTED)))


def test_the_content_names_the_source_and_every_evidence_id_in_order_and_not_the_text():
    candidate = intake()
    records = evidence_from_herald_export(candidate.source, EXPORT, trusted_keys=TRUSTED)
    content = intake_content(candidate.source, records)
    assert content["source_id"] == "inv-1" and content["evidence_ids"] == [r.evidence_id for r in records]
    assert TEXT not in json.dumps(content)


def test_an_export_offered_with_different_text_is_a_breach():
    result = check(intake(text=TEXT + " changed"))
    assert result.outcome is gate.GateOutcome.TERMINAL_BREACH and "different text" in result.reason


def test_an_edited_export_is_a_breach():
    edited = json.loads(json.dumps(EXPORT))
    edited["admitted"][0]["raw"] = "INV-9999"
    assert check(intake(export=edited)).outcome is gate.GateOutcome.TERMINAL_BREACH


def test_an_export_no_pinned_key_signed_is_a_breach_and_no_keys_is_a_breach():
    other = {k: v for k, v in TRUSTED.items()}
    other.clear()
    assert check(intake(), trusted=other).outcome is gate.GateOutcome.TERMINAL_BREACH


def test_an_export_that_cannot_be_read_at_all_is_a_breach_and_never_a_pass():
    for broken in ({}, {"admitted": 7}, {"admitted": [None]}):
        assert check(intake(export=broken)).outcome is gate.GateOutcome.TERMINAL_BREACH


def test_a_refusal_is_still_bound_to_the_source_it_judged_so_it_cannot_pass_for_another():
    refused = check(intake(text=TEXT + " changed"))
    assert refused.bound() and refused.subject == INTAKE_SUBJECT
    assert refused.subject_digest != check(intake()).subject_digest


def test_two_different_sources_never_share_a_digest():
    a, b = check(intake(source_id="inv-1")), check(intake(source_id="inv-2"))
    assert a.subject_digest != b.subject_digest


def test_the_same_intake_twice_gives_the_same_verdict():
    assert check(intake()).subject_digest == check(intake()).subject_digest


def test_a_candidate_that_is_not_an_intake_is_a_type_error():
    with pytest.raises(TypeError, match="HeraldIntake"):
        check("not an intake")


def test_the_gate_judges_and_writes_nothing():
    candidate = intake()
    before = json.dumps(EXPORT, sort_keys=True)
    check(candidate)
    assert json.dumps(EXPORT, sort_keys=True) == before
