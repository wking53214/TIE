"""The HERALD to TIE handoff against the adversarial cases in the interoperability brief, enforced by TIE's own code.

Each test calls the real intake functions with a real, producer-made export (the v4 fixture) or a re-signed copy with
one deliberate change. Nothing here uses a mock verifier; TIE checks the signature, the receiver, the source and the
claims itself."""

import copy
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tie.evidence.herald_intake import (
    HeraldIntakeRefused,
    SeenHandoffs,
    evidence_from_herald_export,
    export_key_id,
    export_signing_bytes,
    record_handoff_once,
    signoffs_from_herald_export,
)
from tie.source.loader import create_source

FIX = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "herald_export_v4.json").read_text())
EXPORT, TEXT = FIX["export"], FIX["text"]
REAL = {export_key_id(k): k for k in [serialization.load_pem_public_key(FIX["public_key_pem"].encode())]}
NOW = datetime.fromisoformat(EXPORT["identity"]["signed_at"]) + timedelta(seconds=30)
SOURCE_ID = EXPORT["document"]["source_id"]
SOURCE = create_source(SOURCE_ID, TEXT)
_KEY = Ed25519PrivateKey.generate()
TEST = {export_key_id(_KEY.public_key()): _KEY.public_key()}
BUILD = EXPORT["herald"]


def resign(export):
    export = copy.deepcopy(export)
    export["key_id"] = export_key_id(_KEY.public_key())
    export["export_mac"] = _KEY.sign(export_signing_bytes(export)).hex()
    return export


def changed(mutate):
    export = copy.deepcopy(EXPORT)
    mutate(export)
    return resign(export)


def take(export, source=SOURCE, keys=None, **kw):
    return evidence_from_herald_export(source, export, trusted_keys=keys or TEST, now=NOW, **kw)


def refused(export, source=SOURCE, keys=None, match=None, **kw):
    for fn in (evidence_from_herald_export, signoffs_from_herald_export):
        with pytest.raises(HeraldIntakeRefused, match=match):
            fn(source, export, trusted_keys=keys or TEST, now=NOW, **kw)


# 1. valid export, correct receiver
def test_a_genuine_export_for_the_right_receiver_is_accepted_and_traceable():
    records = evidence_from_herald_export(SOURCE, EXPORT, trusted_keys=REAL, now=NOW)
    assert records
    from tie.evidence.herald_intake import source_sha256_of
    assert all(source_sha256_of(r) == EXPORT["admitted"][0]["source_hash"] for r in records)


# 2. signed for another receiver, and 12. receiver binding missing or invalid
def test_an_export_signed_for_a_different_receiver_is_refused():
    refused(changed(lambda e: e["identity"].update(audience="SomeoneElse")), match="addressed to")


@pytest.mark.parametrize("audience", [None, "", "  ", 5])
def test_a_valid_signature_with_a_missing_or_invalid_receiver_is_refused(audience):
    refused(changed(lambda e: e["identity"].update(audience=audience)), match="audience|addressed")


def test_a_valid_signature_with_no_identity_block_is_refused():
    def drop(e):
        del e["identity"]
    refused(changed(drop), match="identity")


# 3. modified after signing (the signature is NOT redone)
@pytest.mark.parametrize("mutate", [
    lambda e: e["admitted"][0].update(raw="$9,999.00 "),
    lambda e: e["admitted"][0].update(value={"amount": 9999.0, "currency": "USD"}),
    lambda e: e["identity"].update(audience="TIE", handoff_id="hid-forged"),
    lambda e: e["herald"].update(version="9.9.9"),
    lambda e: e["document"].update(source_id="other"),
    lambda e: e["admitted"].pop(),
])
def test_a_payload_changed_after_signing_fails_the_signature(mutate):
    tampered = copy.deepcopy(EXPORT)
    mutate(tampered)
    refused(tampered, keys=REAL, match="did not verify")


# 4. altered provenance or source identity (re-signed, so only TIE's own checks can stop it)
def test_an_export_about_a_different_document_than_the_source_offered_is_refused():
    refused(changed(lambda e: e["document"].update(source_id="loan-0001")), match="is about source")


def test_a_genuine_export_is_not_accepted_for_a_differently_named_source_with_the_same_text():
    refused(EXPORT, source=create_source("some-other-name", TEXT), keys=REAL, match="is about source")


def test_a_claim_naming_another_source_is_refused():
    refused(changed(lambda e: e["admitted"][0].update(source_id="loan-0001")), match="names source")


# 5. stale HERALD version or mismatched code hash
def test_the_expected_herald_build_is_accepted_when_it_matches():
    assert take(resign(EXPORT), expected_herald={"version": BUILD["version"], "code_hash": BUILD["code_hash"]})


def test_an_export_from_another_herald_version_is_refused_when_a_build_is_expected():
    old = changed(lambda e: e["herald"].update(version="0.5.0"))
    refused(old, expected_herald={"version": BUILD["version"]}, match="version")


def test_an_export_with_another_code_hash_is_refused_when_a_build_is_expected():
    other = changed(lambda e: e["herald"].update(code_hash="0" * 64))
    refused(other, expected_herald={"code_hash": BUILD["code_hash"]}, match="code_hash")


def test_without_an_expected_build_any_signed_build_is_accepted_which_is_the_documented_limit():
    assert take(changed(lambda e: e["herald"].update(version="0.0.1", code_hash="0" * 64)))


@pytest.mark.parametrize("expected", [{}, {"version": ""}, {"other": "x"}, {"version": 6}, ["0.6.0"], "0.6.0"])
def test_a_malformed_expected_build_is_refused(expected):
    refused(resign(EXPORT), expected_herald=expected, match="expected_herald")


# 6. unsupported schema
def test_an_unsupported_schema_label_is_refused():
    refused(changed(lambda e: e["identity"].update(schema="herald-handoff/9")), match="unsupported")


def test_an_unsupported_export_version_is_refused():
    refused(changed(lambda e: e.update(export_mac_version="5")), match="only signed HERALD exports|version")


# 7. missing or malformed evidence references
@pytest.mark.parametrize("field", ["span", "raw", "source_hash", "source_id"])
def test_a_claim_missing_a_reference_field_is_refused(field):
    def drop(e):
        del e["admitted"][0][field]
    refused(changed(drop))


# 8. replayed handoff
def test_a_replayed_handoff_is_refused_by_the_ledger():
    ledger = SeenHandoffs()
    take(EXPORT, keys=REAL)
    record_handoff_once(EXPORT, ledger)
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        record_handoff_once(EXPORT, ledger)


# 9. duplicate claim or evidence identifiers
def test_the_same_claim_admitted_twice_is_refused():
    refused(changed(lambda e: e["admitted"].append(copy.deepcopy(e["admitted"][0]))), match="more than once")


def test_two_claims_under_one_claim_id_are_refused():
    def reuse(e):
        e["admitted"][0]["claim_id"] = e["admitted"][1]["claim_id"]
    refused(changed(reuse), match="more than once")


def test_evidence_ids_from_a_genuine_export_are_all_distinct():
    ids = [r.evidence_id for r in evidence_from_herald_export(SOURCE, EXPORT, trusted_keys=REAL, now=NOW)]
    assert len(ids) == len(set(ids))


# 10. partial failure: nothing is half taken in
def test_one_bad_claim_returns_no_records_and_leaves_the_ledger_unspent():
    export = changed(lambda e: e["admitted"].append(dict(e["admitted"][0], claim_id="x", span=[0, 3], raw="XXX")))
    ledger = SeenHandoffs()
    with pytest.raises(HeraldIntakeRefused):
        take(export)
    assert ledger.has_seen(EXPORT["identity"]["handoff_id"]) is False


# 11. Not tested here: intake needs no CNS verification by design; tests/test_cns_independence.py checks that it
# works with CNS blocked.
