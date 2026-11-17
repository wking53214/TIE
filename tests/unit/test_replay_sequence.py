"""The caller sequence for taking in a HERALD handoff, and what it does when a step fails.

Required order, because TIE does not do it for you:
  1. Verify and accept the export (evidence_from_herald_export and/or signoffs_from_herald_export). A refusal ends it.
  2. Hold the resulting records.
  3. Claim the handoff ID through the ledger, once (record_handoff_once).
  4. Pass the records downstream only after the claim succeeded.

These tests describe today's behaviour, including two hazards that need a decision from the deployer or the owner;
they are asserted so a future change to either one is a visible change, not a silent one."""

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
PINNED = {export_key_id(k): k for k in [serialization.load_pem_public_key(FIX["public_key_pem"].encode())]}
NOW = datetime.fromisoformat(EXPORT["identity"]["signed_at"]) + timedelta(seconds=30)
SOURCE = create_source(EXPORT["document"]["source_id"], TEXT)


def take_in(export, ledger, keys=PINNED):
    """The documented caller sequence, in order. Returns what may go downstream."""
    records = evidence_from_herald_export(SOURCE, export, trusted_keys=keys, now=NOW)    # 1 and 2
    signoffs = signoffs_from_herald_export(SOURCE, export, trusted_keys=keys, now=NOW)
    record_handoff_once(export, ledger)                                                   # 3
    return records, signoffs                                                              # 4


def test_the_documented_sequence_takes_an_export_in_once():
    ledger = SeenHandoffs()
    records, _ = take_in(EXPORT, ledger)
    assert records
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        take_in(EXPORT, ledger)


def test_reading_before_claiming_does_not_claim():
    """Intake is read-only with respect to the ledger: only record_handoff_once spends the ID."""
    ledger = SeenHandoffs()
    evidence_from_herald_export(SOURCE, EXPORT, trusted_keys=PINNED, now=NOW)
    signoffs_from_herald_export(SOURCE, EXPORT, trusted_keys=PINNED, now=NOW)
    assert ledger.has_seen(EXPORT["identity"]["handoff_id"]) is False


def test_a_refused_export_must_not_be_claimed_and_the_sequence_stops_before_the_claim():
    ledger = SeenHandoffs()
    with pytest.raises(HeraldIntakeRefused):
        take_in(EXPORT, ledger, keys={})  # no trusted keys: step 1 refuses
    assert ledger.has_seen(EXPORT["identity"]["handoff_id"]) is False


def test_HAZARD_record_handoff_once_does_not_verify_the_export_so_a_forged_one_can_spend_a_real_id():
    """record_handoff_once reads only the ID and the version label; it checks no signature. Anyone able to call it
    with an unverified export (or any dict carrying the ID) can spend a genuine handoff ID before the real export is
    taken in, which refuses the real one. The remedy is the caller's order (verify first, as above) or a change to the
    function so it verifies; changing it alters the public API, so it is left as an owner decision."""
    key = Ed25519PrivateKey.generate()
    forged = dict(EXPORT, export_mac=key.sign(export_signing_bytes(EXPORT)).hex())  # wrong signature, same ID
    with pytest.raises(HeraldIntakeRefused):
        evidence_from_herald_export(SOURCE, forged, trusted_keys=PINNED, now=NOW)   # intake rejects it ...
    ledger = SeenHandoffs()
    record_handoff_once(forged, ledger)                                              # ... but the claim accepts it
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        take_in(EXPORT, ledger)                                                      # and the real export is refused


def test_HAZARD_a_failure_after_the_claim_cannot_be_retried_with_the_same_ledger():
    """The claim is at-most-once. If the caller claims and then fails to pass the records on (crash, bad downstream),
    the handoff is spent and a retry is refused. A deployment that needs at-least-once must release or journal the claim
    in its own ledger; TIE's contract has no release operation, and adding one is an architectural decision."""
    ledger = SeenHandoffs()
    records, _ = take_in(EXPORT, ledger)

    def downstream(_records):
        raise RuntimeError("downstream failed")

    with pytest.raises(RuntimeError):
        downstream(records)
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        take_in(EXPORT, ledger)


def test_claiming_before_verifying_is_the_wrong_order_and_is_not_undone_by_a_later_refusal():
    ledger = SeenHandoffs()
    record_handoff_once(EXPORT, ledger)                      # wrong order: claim first
    with pytest.raises(HeraldIntakeRefused):
        evidence_from_herald_export(SOURCE, EXPORT, trusted_keys={}, now=NOW)  # then intake refuses
    assert ledger.has_seen(EXPORT["identity"]["handoff_id"]) is True          # the ID stays spent


def test_record_handoff_once_with_trusted_keys_refuses_a_forged_export_and_spends_nothing():
    """The remedy for the hazard above: with trusted_keys the claim verifies first."""
    key = Ed25519PrivateKey.generate()
    forged = dict(EXPORT, export_mac=key.sign(export_signing_bytes(EXPORT)).hex())
    ledger = SeenHandoffs()
    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        record_handoff_once(forged, ledger, trusted_keys=PINNED, now=NOW)
    assert ledger.has_seen(EXPORT["identity"]["handoff_id"]) is False
    take_in(EXPORT, ledger)  # the real export is still taken in


def test_record_handoff_once_with_trusted_keys_refuses_other_audience_and_stale_exports():
    ledger = SeenHandoffs()
    with pytest.raises(HeraldIntakeRefused, match="addressed"):
        record_handoff_once(EXPORT, ledger, trusted_keys=PINNED, audience="SOMEONE_ELSE", now=NOW)
    with pytest.raises(HeraldIntakeRefused):
        record_handoff_once(EXPORT, ledger, trusted_keys=PINNED, max_age_seconds=1,
                            now=NOW + __import__("datetime").timedelta(hours=2))
    assert ledger.has_seen(EXPORT["identity"]["handoff_id"]) is False


def test_record_handoff_once_with_trusted_keys_still_claims_once_for_a_genuine_export():
    ledger = SeenHandoffs()
    record_handoff_once(EXPORT, ledger, trusted_keys=PINNED, now=NOW)
    with pytest.raises(HeraldIntakeRefused, match="already taken in"):
        record_handoff_once(EXPORT, ledger, trusted_keys=PINNED, now=NOW)
