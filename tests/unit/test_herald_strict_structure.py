"""Malformed input and bad configuration end in a controlled refusal, never a Python error or a partial admission.

The signing time is the signer's own assertion, not a time vouched for by an independent authority; these tests check
what TIE does with that assertion, not that it is true."""

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tie.evidence.herald_intake import (
    MAX_AGE_LIMIT_SECONDS,
    V3_SUNSET,
    HeraldIntakeRefused,
    evidence_from_herald_export,
    export_key_id,
    export_signing_bytes,
    signoffs_from_herald_export,
)
from tie.source.loader import create_source

_FIX = Path(__file__).resolve().parents[1] / "fixtures"
V4 = json.loads((_FIX / "herald_export_v4.json").read_text())
V3 = json.loads((_FIX / "herald_export.json").read_text())
EXPORT = V4["export"]
SIGNED_AT = datetime.fromisoformat(EXPORT["identity"]["signed_at"])
NOW = SIGNED_AT + timedelta(seconds=30)
V4_PINNED = {export_key_id(k): k for k in [serialization.load_pem_public_key(V4["public_key_pem"].encode())]}
V3_PINNED = {export_key_id(k): k for k in [serialization.load_pem_public_key(V3["public_key_pem"].encode())]}

_KEY_A = Ed25519PrivateKey.generate()
_KEY_B = Ed25519PrivateKey.generate()
KEY_A = {export_key_id(_KEY_A.public_key()): _KEY_A.public_key()}
KEY_B = {export_key_id(_KEY_B.public_key()): _KEY_B.public_key()}


def _source():
    return create_source(EXPORT["document"]["source_id"], V4["text"])


def _signed(export, key=_KEY_A):
    export = copy.deepcopy(export)
    export["key_id"] = export_key_id(key.public_key())
    export["export_mac"] = key.sign(export_signing_bytes(export)).hex()
    return export


def _both(export, trusted=None, **kw):
    """Run both intake paths; return the exception each raised (or None)."""
    kw = {"trusted_keys": KEY_A if trusted is None else trusted, "now": NOW, **kw}
    seen = []
    for fn in (evidence_from_herald_export, signoffs_from_herald_export):
        try:
            fn(_source(), export, **kw)
            seen.append(None)
        except Exception as exc:  # noqa: BLE001  the point is to see exactly what comes out
            seen.append(exc)
    return seen


def _all_refused(results):
    return all(isinstance(r, HeraldIntakeRefused) for r in results)


def test_the_baseline_export_is_accepted_when_signed_by_the_test_key():
    assert _both(_signed(EXPORT)) == [None, None]


@pytest.mark.parametrize("bad", [None, [], "export", 5, 1.5])
def test_an_export_that_is_not_an_object_is_refused(bad):
    assert _all_refused(_both(bad))


@pytest.mark.parametrize("admitted", [None, 5, "abc", {"a": 1}, [None], ["x"], [5], [[]]])
def test_a_malformed_admitted_collection_is_refused(admitted):
    export = copy.deepcopy(EXPORT)
    export["admitted"] = admitted
    assert _all_refused(_both(_signed(export)))


@pytest.mark.parametrize("changes", [
    {"kind": 5}, {"kind": ""}, {"kind": None}, {"source_hash": 5}, {"source_hash": None},
    {"reading": ["EXTRACTED"]}, {"reading": 5}, {"segment": ["a"]}, {"segment": 5},
])
def test_a_malformed_entry_field_is_refused(changes):
    export = copy.deepcopy(EXPORT)
    export["admitted"][0].update(changes)
    assert _all_refused(_both(_signed(export)))


@pytest.mark.parametrize("field", ["kind", "source_hash"])
def test_a_missing_required_entry_field_is_refused(field):
    export = copy.deepcopy(EXPORT)
    del export["admitted"][0][field]
    assert _all_refused(_both(_signed(export)))


def test_a_malformed_second_entry_admits_nothing_from_the_first():
    export = copy.deepcopy(EXPORT)
    export["admitted"].append("not an entry")
    assert _all_refused(_both(_signed(export)))


@pytest.mark.parametrize("age", [None, -1, 0, "60", float("nan"), float("inf"), 10**18, True, 1.5,
                                 MAX_AGE_LIMIT_SECONDS + 1])
def test_a_bad_max_age_is_refused(age):
    assert _all_refused(_both(_signed(EXPORT), max_age_seconds=age))


@pytest.mark.parametrize("audience", [None, "", "   ", 5, ["TIE"]])
def test_a_bad_audience_is_refused(audience):
    assert _all_refused(_both(_signed(EXPORT), audience=audience))


@pytest.mark.parametrize("now", [datetime(2026, 11, 16), "now", 5])  # noqa: DTZ001  naive on purpose
def test_a_bad_now_is_refused(now):
    assert _all_refused(_both(_signed(EXPORT), now=now))


@pytest.mark.parametrize("keys", [[1], "key", 5])
def test_trusted_keys_of_the_wrong_type_are_refused(keys):
    assert _all_refused(_both(_signed(EXPORT), trusted=keys))


def test_the_extreme_valid_ages_are_accepted():
    assert _both(_signed(EXPORT), now=SIGNED_AT, max_age_seconds=1) == [None, None]
    assert _both(_signed(EXPORT), max_age_seconds=MAX_AGE_LIMIT_SECONDS) == [None, None]


# --- the signing time is the signer's claim; check how TIE treats it -------------------------------------------------

def _with_signed_at(value):
    export = copy.deepcopy(EXPORT)
    export["identity"]["signed_at"] = value
    return _signed(export)


@pytest.mark.parametrize("value", ["2026-11-16T10:00:00", "yesterday", "", "2026-13-45T99:99:99+00:00", 5, None])
def test_an_unusable_signing_time_is_refused(value):
    assert _all_refused(_both(_with_signed_at(value)))


def test_the_far_future_and_far_past_are_refused_not_crashed():
    assert _all_refused(_both(_with_signed_at("9999-12-31T23:59:59+00:00")))
    assert _all_refused(_both(_with_signed_at("0001-01-01T00:00:00+00:00")))


def test_the_same_instant_in_another_time_zone_is_accepted():
    other = SIGNED_AT.astimezone(timezone(timedelta(hours=-9, minutes=-30)))
    assert other.isoformat() != SIGNED_AT.isoformat()
    assert _both(_with_signed_at(other.isoformat())) == [None, None]


def test_the_age_limit_is_inclusive_and_exact():
    age = 600
    at_limit = SIGNED_AT + timedelta(seconds=age)
    assert _both(_signed(EXPORT), now=at_limit, max_age_seconds=age) == [None, None]
    over = at_limit + timedelta(microseconds=1)
    assert _all_refused(_both(_signed(EXPORT), now=over, max_age_seconds=age))


def test_the_future_skew_limit_is_inclusive_and_exact():
    skew = timedelta(minutes=5)
    just_inside = SIGNED_AT - skew
    assert _both(_signed(EXPORT), now=just_inside) == [None, None]
    assert _all_refused(_both(_signed(EXPORT), now=just_inside - timedelta(microseconds=1)))


# --- version 3 and its sunset ----------------------------------------------------------------------------------------

def _v3(now):
    results = []
    for fn in (evidence_from_herald_export, signoffs_from_herald_export):
        try:
            fn(create_source(V3["export"]["document"]["source_id"], V3["text"]), V3["export"],
               trusted_keys=V3_PINNED, now=now)
            results.append(None)
        except Exception as exc:  # noqa: BLE001  same: record whatever comes out
            results.append(exc)
    return results


def test_version_3_is_accepted_up_to_and_including_the_exact_sunset_instant():
    assert _v3(V3_SUNSET - timedelta(days=30)) == [None, None]
    assert _v3(V3_SUNSET) == [None, None]


def test_version_3_is_refused_the_instant_after_the_sunset():
    assert _all_refused(_v3(V3_SUNSET + timedelta(microseconds=1)))


# --- key rotation and several trusted keys ---------------------------------------------------------------------------

def test_an_export_signed_by_either_of_two_pinned_keys_is_accepted():
    both = {**KEY_A, **KEY_B}
    assert _both(_signed(EXPORT, _KEY_A), trusted=both) == [None, None]
    assert _both(_signed(EXPORT, _KEY_B), trusted=both) == [None, None]


def test_after_rotation_the_retired_key_is_no_longer_trusted():
    old_export = _signed(EXPORT, _KEY_A)
    assert _both(old_export, trusted={**KEY_A, **KEY_B}) == [None, None]
    assert _all_refused(_both(old_export, trusted=KEY_B))


def test_a_key_id_that_names_one_key_but_a_signature_from_another_is_refused():
    export = _signed(EXPORT, _KEY_B)
    export["key_id"] = export_key_id(_KEY_A.public_key())
    assert _all_refused(_both(export, trusted={**KEY_A, **KEY_B}))
