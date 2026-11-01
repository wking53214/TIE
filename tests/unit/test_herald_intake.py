"""HERALD intake: admitted claims become TIE evidence, and nothing else does.

The fixture is a real HERALD export (tests/fixtures/herald_export.json).
"""

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tie.evidence.herald_intake import (
    HeraldIntakeRefused,
    evidence_from_herald_export,
    export_key_id,
    export_signing_bytes,
)
from tie.models import EpistemicStatus
from tie.source.loader import create_source

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "herald_export.json").read_text()
)
TEXT = FIXTURE["text"]
EXPORT = FIXTURE["export"]

# The fixture is a real version 3 export from HERALD (signed by HERALD's own code; only its public key is kept here).
_FIXTURE_PUB = serialization.load_pem_public_key(FIXTURE["public_key_pem"].encode())
FIXTURE_TRUSTED = {export_key_id(_FIXTURE_PUB): _FIXTURE_PUB}

# A test-only key, generated fresh on each run and never stored, so tests can make a validly signed export that
# has been changed on purpose. It proves nothing about HERALD: it stands in for a second HERALD key.
_TEST_KEY = Ed25519PrivateKey.generate()
_TEST_PUB = _TEST_KEY.public_key()
TEST_TRUSTED = {export_key_id(_TEST_PUB): _TEST_PUB}
ALL_TRUSTED = {**FIXTURE_TRUSTED, **TEST_TRUSTED}


def resigned(export):
    """Sign `export` with the test key, as HERALD would: after this a deliberate change is a valid export."""
    export = json.loads(json.dumps(export))
    export["export_mac_version"] = "3"
    export["key_id"] = export_key_id(_TEST_PUB)
    export["export_mac"] = _TEST_KEY.sign(export_signing_bytes(export)).hex()
    return export


def _source():
    return create_source("inv-1", TEXT)


def test_the_real_herald_export_is_accepted_by_its_pinned_key():
    records = evidence_from_herald_export(_source(), EXPORT, trusted_keys=FIXTURE_TRUSTED)
    assert len(records) == len(EXPORT["admitted"]) == 1


def test_each_machine_record_names_the_source_hash_tie_verified_it_against():
    import hashlib

    [record] = evidence_from_herald_export(_source(), EXPORT, trusted_keys=FIXTURE_TRUSTED)
    assert f"source_sha256: {hashlib.sha256(TEXT.encode('utf-8')).hexdigest()}" in record.notes


def test_refuses_without_trusted_keys():
    with pytest.raises(HeraldIntakeRefused, match="no trusted HERALD export keys"):
        evidence_from_herald_export(_source(), EXPORT, trusted_keys={})


def test_the_caller_cannot_pass_a_verifier_function_any_more():
    with pytest.raises(TypeError):
        evidence_from_herald_export(_source(), EXPORT, verify=lambda _export: None, trusted_keys=FIXTURE_TRUSTED)


def test_an_altered_signed_export_is_refused():
    tampered = json.loads(json.dumps(EXPORT))
    tampered["admitted"][0]["raw"] = "$9,999.00"
    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        evidence_from_herald_export(_source(), tampered, trusted_keys=FIXTURE_TRUSTED)


def test_an_export_signed_by_an_untrusted_key_is_refused_by_name():
    with pytest.raises(HeraldIntakeRefused, match="not trusted"):
        evidence_from_herald_export(_source(), EXPORT, trusted_keys=TEST_TRUSTED)


def test_an_unsigned_or_version_2_export_is_refused():
    legacy = json.loads(json.dumps(EXPORT))
    legacy["export_mac_version"] = "2"
    with pytest.raises(HeraldIntakeRefused, match="only signed HERALD exports"):
        evidence_from_herald_export(_source(), legacy, trusted_keys=FIXTURE_TRUSTED)


def test_the_signing_bytes_match_the_vector_herald_also_checks():
    vector = export_signing_bytes({"document": {"source_id": "d"}, "herald": {"version": "v"}, "admitted": [],
                                   "refused": [], "key_id": "ed25519-0000000000000000"})
    assert vector == (b'{"admitted":[],"document":{"source_id":"d"},"export_mac_version":"3",'
                      b'"herald":{"version":"v"},"key_id":"ed25519-0000000000000000","refused":[]}')


def test_admitted_claims_become_inferred_evidence():
    records = evidence_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED)
    assert len(records) == len(EXPORT["admitted"]) == 1
    record = records[0]
    assert record.epistemic_status is EpistemicStatus.INFERRED
    assert record.evidence_id.startswith("herald-")
    assert EXPORT["admitted"][0]["raw"] in record.statement


@pytest.mark.parametrize("reading", ["HUMAN_CONFIRMED", "WEIRD", None])
def test_only_machine_readings_enter(reading):
    export = json.loads(json.dumps(EXPORT))
    export["admitted"][0]["reading"] = reading
    assert evidence_from_herald_export(_source(), resigned(export), trusted_keys=TEST_TRUSTED) == []


def test_replaying_the_same_export_gives_the_same_evidence_ids():
    first = evidence_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED)
    second = evidence_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED)
    assert [r.evidence_id for r in first] == [r.evidence_id for r in second]


def test_same_claim_at_a_different_span_gets_a_different_id():
    moved = json.loads(json.dumps(EXPORT))
    moved["admitted"][0]["span"] = [moved["admitted"][0]["span"][0] + 1, moved["admitted"][0]["span"][1] + 1]
    moved = resigned(moved)
    original = evidence_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED)[0].evidence_id
    shifted = evidence_from_herald_export(_source(), moved, trusted_keys=ALL_TRUSTED)[0].evidence_id
    assert original != shifted


def test_refused_claims_never_enter():
    assert EXPORT["refused"], "fixture should include a refused claim"
    records = evidence_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED)
    refused_ids = {f"herald-{r['claim_id']}" for r in EXPORT["refused"]}
    assert not refused_ids & {r.evidence_id for r in records}


def test_a_claim_from_different_text_is_refused():
    other = create_source("inv-1", TEXT + " Extra sentence changes the hash.")
    with pytest.raises(HeraldIntakeRefused, match="different text"):
        evidence_from_herald_export(other, EXPORT, trusted_keys=ALL_TRUSTED)


# --- Human sign-offs: a separate path, never mixed with machine readings -----

from tie.evidence.herald_intake import SIGNOFF_READING, signoffs_from_herald_export  # noqa: E402
from tie.models import OriginKind  # noqa: E402


def _signed_off(who="alice@example.com", value="2026-11-01"):
    export = json.loads(json.dumps(EXPORT))
    entry = export["admitted"][0]
    entry["reading"] = SIGNOFF_READING
    entry["confirmed_by"] = who
    entry["confirmation_rationale"] = "checked against the paper invoice"
    entry["confirmed_at"] = "2026-10-29T12:00:00+00:00"
    entry["value"] = value
    return resigned(export)


def test_signoff_path_refuses_without_trusted_keys():
    with pytest.raises(HeraldIntakeRefused, match="no trusted HERALD export keys"):
        signoffs_from_herald_export(_source(), _signed_off(), trusted_keys={})


def test_signoff_path_refuses_a_tampered_signed_export():
    tampered = _signed_off()
    tampered["admitted"][0]["confirmed_by"] = "mallory@example.com"    # changed after signing
    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        signoffs_from_herald_export(_source(), tampered, trusted_keys=ALL_TRUSTED)


def test_a_signoff_becomes_human_accepted_evidence_naming_the_confirmer():
    records = signoffs_from_herald_export(_source(), _signed_off(), trusted_keys=ALL_TRUSTED)
    assert len(records) == 1
    record = records[0]
    assert record.provenance.origin is OriginKind.HUMAN_ACCEPTED_AI
    assert record.evidence_id.startswith("signoff-")
    assert "confirmed_by: alice@example.com" in record.notes
    assert any(n.startswith("confirmed_value: ") and "2026-11-01" in n for n in record.notes)
    assert f"herald_claim_id: {EXPORT['admitted'][0]['claim_id']}" in record.notes


def test_signoffs_never_come_out_of_the_machine_path_and_the_reverse():
    signed = _signed_off()
    assert evidence_from_herald_export(_source(), signed, trusted_keys=ALL_TRUSTED) == []
    assert signoffs_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED) == []


def test_a_signoff_that_names_no_one_is_refused_not_skipped():
    for who in (None, "", "   ", 7):
        export = _signed_off()
        export["admitted"][0]["confirmed_by"] = who
        export = resigned(export)
        with pytest.raises(HeraldIntakeRefused, match="names no one"):
            signoffs_from_herald_export(_source(), export, trusted_keys=ALL_TRUSTED)


@pytest.mark.parametrize("field,why", [("confirmation_rationale", "gives no reason"), ("confirmed_at", "gives no time")])
@pytest.mark.parametrize("bad", [None, "", "  "])
def test_a_signoff_with_no_reason_or_no_time_is_refused_not_skipped(field, why, bad):
    export = _signed_off()
    export["admitted"][0][field] = bad
    export = resigned(export)
    with pytest.raises(HeraldIntakeRefused, match=why):
        signoffs_from_herald_export(_source(), export, trusted_keys=ALL_TRUSTED)


def test_the_reason_and_the_time_are_recorded_on_the_evidence():
    record = signoffs_from_herald_export(_source(), _signed_off(), trusted_keys=ALL_TRUSTED)[0]
    assert "confirmed_because: checked against the paper invoice" in record.notes
    assert "confirmed_at: 2026-10-29T12:00:00+00:00" in record.notes


def test_a_signoff_missing_the_confirmer_key_is_refused():
    export = _signed_off()
    del export["admitted"][0]["confirmed_by"]
    export = resigned(export)
    with pytest.raises(HeraldIntakeRefused, match="names no one"):
        signoffs_from_herald_export(_source(), export, trusted_keys=ALL_TRUSTED)


def test_a_signoff_from_different_text_is_refused():
    with pytest.raises(HeraldIntakeRefused, match="different text"):
        signoffs_from_herald_export(create_source("inv-1", TEXT + " edited"), _signed_off(), trusted_keys=ALL_TRUSTED)


def test_two_people_confirming_the_same_claim_are_two_records():
    a = signoffs_from_herald_export(_source(), _signed_off("alice@example.com"), trusted_keys=ALL_TRUSTED)[0]
    b = signoffs_from_herald_export(_source(), _signed_off("bob@example.com"), trusted_keys=ALL_TRUSTED)[0]
    assert a.evidence_id != b.evidence_id


def test_replaying_a_signoff_gives_the_same_id():
    first = signoffs_from_herald_export(_source(), _signed_off(), trusted_keys=ALL_TRUSTED)
    second = signoffs_from_herald_export(_source(), _signed_off(), trusted_keys=ALL_TRUSTED)
    assert [r.evidence_id for r in first] == [r.evidence_id for r in second]


def test_a_signoff_id_never_equals_a_machine_reading_id():
    machine = evidence_from_herald_export(_source(), EXPORT, trusted_keys=ALL_TRUSTED)[0].evidence_id
    signed = signoffs_from_herald_export(_source(), _signed_off(), trusted_keys=ALL_TRUSTED)[0].evidence_id
    assert machine != signed
