"""Version 4 HERALD exports: a signed handoff ID, signing time and audience, checked by TIE alone.

The fixture (tests/fixtures/herald_export_v4.json) was produced by HERALD in its own process with a key that was then
discarded; this file holds only the public key. TIE's code is the only code running here, as on a separate machine.
"""

import copy
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import tie.evidence.herald_intake as intake
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

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "herald_export_v4.json").read_text())
TEXT = FIXTURE["text"]
EXPORT = FIXTURE["export"]
PUB = serialization.load_pem_public_key(FIXTURE["public_key_pem"].encode())
PINNED = {export_key_id(PUB): PUB}
SIGNED_AT = datetime.fromisoformat(EXPORT["identity"]["signed_at"])
JUST_AFTER = SIGNED_AT + timedelta(seconds=30)

_KEY = Ed25519PrivateKey.generate()
_KEY_PINNED = {export_key_id(_KEY.public_key()): _KEY.public_key()}


def _source():
    return create_source(EXPORT["document"]["source_id"], TEXT)


def _resigned(export):
    """Sign a deliberately changed export with a test key, so the change reaches the identity checks."""
    export = copy.deepcopy(export)
    export["key_id"] = export_key_id(_KEY.public_key())
    export["export_mac"] = _KEY.sign(export_signing_bytes(export)).hex()
    return export


def _take(export=EXPORT, trusted=PINNED, **kw):
    return evidence_from_herald_export(_source(), export, trusted_keys=trusted, now=JUST_AFTER, **kw)


def test_a_genuine_version_4_export_is_accepted_for_its_audience_and_time():
    assert len(_take()) == len(EXPORT["admitted"]) == 2
    assert EXPORT["export_mac_version"] == "4"


def test_signoffs_path_applies_the_same_identity_checks():
    with pytest.raises(HeraldIntakeRefused, match="addressed to"):
        signoffs_from_herald_export(_source(), EXPORT, trusted_keys=PINNED, now=JUST_AFTER, audience="Other")


@pytest.mark.parametrize("field,new", [("handoff_id", "hid-forged"), ("signed_at", "2026-11-17T09:00:00+00:00"),
                                       ("audience", "Other")])
def test_altering_a_signed_identity_field_is_refused(field, new):
    tampered = copy.deepcopy(EXPORT)
    tampered["identity"][field] = new
    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        _take(tampered)


def test_an_export_addressed_to_someone_else_is_refused_even_when_validly_signed():
    other = copy.deepcopy(EXPORT)
    other["identity"]["audience"] = "SomeoneElse"
    with pytest.raises(HeraldIntakeRefused, match="not to 'TIE'"):
        _take(_resigned(other), trusted=_KEY_PINNED)


def test_a_receiver_can_name_itself_something_other_than_tie():
    with pytest.raises(HeraldIntakeRefused, match="addressed to 'TIE', not to 'Archive'"):
        _take(audience="Archive")


def test_a_stale_export_is_refused_and_the_window_is_the_deployers_to_set():
    later = SIGNED_AT + timedelta(hours=25)
    with pytest.raises(HeraldIntakeRefused, match="ask for a fresh one"):
        evidence_from_herald_export(_source(), EXPORT, trusted_keys=PINNED, now=later)
    assert len(evidence_from_herald_export(_source(), EXPORT, trusted_keys=PINNED, now=later,
                                           max_age_seconds=48 * 3600)) == 2


def test_an_export_signed_in_the_future_is_refused_but_small_clock_difference_is_not():
    with pytest.raises(HeraldIntakeRefused, match="in the future"):
        evidence_from_herald_export(_source(), EXPORT, trusted_keys=PINNED, now=SIGNED_AT - timedelta(minutes=10))
    assert len(evidence_from_herald_export(_source(), EXPORT, trusted_keys=PINNED,
                                           now=SIGNED_AT - timedelta(minutes=2))) == 2


def test_a_missing_or_blank_identity_block_is_refused():
    no_block = copy.deepcopy(EXPORT)
    del no_block["identity"]
    with pytest.raises(HeraldIntakeRefused, match="no identity block"):
        _take(_resigned(no_block), trusted=_KEY_PINNED)
    blank = copy.deepcopy(EXPORT)
    blank["identity"]["handoff_id"] = ""
    with pytest.raises(HeraldIntakeRefused, match="no handoff_id"):
        _take(_resigned(blank), trusted=_KEY_PINNED)


def test_an_unsupported_schema_label_is_refused():
    odd = copy.deepcopy(EXPORT)
    odd["identity"]["schema"] = "herald-handoff/9"
    with pytest.raises(HeraldIntakeRefused, match="unsupported HERALD export schema"):
        _take(_resigned(odd), trusted=_KEY_PINNED)


def test_replay_is_refused_when_the_receiver_keeps_a_ledger():
    seen = SeenHandoffs()
    _take()
    record_handoff_once(EXPORT, seen)
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        record_handoff_once(EXPORT, seen)


def test_reading_one_export_twice_is_not_a_replay():
    """Machine readings and sign-offs both read the same export; only record_handoff_once counts."""
    seen = SeenHandoffs()
    _take()
    signoffs_from_herald_export(_source(), EXPORT, trusted_keys=PINNED, now=JUST_AFTER)
    record_handoff_once(EXPORT, seen)


def test_a_version_3_export_has_no_id_to_track():
    v3 = {"export_mac_version": "3"}
    with pytest.raises(HeraldIntakeRefused, match="only a version 4"):
        record_handoff_once(v3, SeenHandoffs())


def test_version_4_signing_bytes_match_the_vector_herald_also_checks():
    vector = export_signing_bytes({
        "export_mac_version": "4", "document": {"source_id": "d"}, "herald": {"version": "v"}, "admitted": [],
        "refused": [], "key_id": "ed25519-abc",
        "identity": {"handoff_id": "hid-0001", "signed_at": "2026-11-17T00:00:00+00:00", "audience": "TIE",
                     "schema": "herald-handoff/4"}})
    assert vector == (
        b'{"admitted":[],"document":{"source_id":"d"},"export_mac_version":"4","herald":{"version":"v"},'
        b'"identity":{"audience":"TIE","handoff_id":"hid-0001","schema":"herald-handoff/4",'
        b'"signed_at":"2026-11-17T00:00:00+00:00"},"key_id":"ed25519-abc","refused":[]}')


def test_a_version_3_export_is_accepted_with_a_warning_before_the_sunset(caplog):
    v3 = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "herald_export.json").read_text())
    pub = serialization.load_pem_public_key(v3["public_key_pem"].encode())
    with caplog.at_level(logging.WARNING):
        records = evidence_from_herald_export(
            create_source("inv-1", v3["text"]), v3["export"], trusted_keys={export_key_id(pub): pub},
            now=intake.V3_SUNSET - timedelta(days=1))
    assert len(records) == 1 and "version 3 export accepted" in caplog.text


def test_a_version_3_export_is_refused_after_the_sunset():
    v3 = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "herald_export.json").read_text())
    pub = serialization.load_pem_public_key(v3["public_key_pem"].encode())
    with pytest.raises(HeraldIntakeRefused, match="no longer accepted"):
        evidence_from_herald_export(
            create_source("inv-1", v3["text"]), v3["export"], trusted_keys={export_key_id(pub): pub},
            now=intake.V3_SUNSET + timedelta(seconds=1))


def test_a_version_3_relabelled_as_version_4_is_refused():
    v3 = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "herald_export.json").read_text())
    pub = serialization.load_pem_public_key(v3["public_key_pem"].encode())
    export = copy.deepcopy(v3["export"])
    export["export_mac_version"] = "4"
    export["identity"] = copy.deepcopy(EXPORT["identity"])
    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        evidence_from_herald_export(create_source("inv-1", v3["text"]), export,
                                    trusted_keys={export_key_id(pub): pub}, now=JUST_AFTER)
