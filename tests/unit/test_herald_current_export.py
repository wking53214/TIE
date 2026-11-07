"""TIE accepts a version 3 export made by the current HERALD, checked with only the pinned public key.

The fixture (tests/fixtures/herald_export_current.json) was produced by HERALD in its own process. The signing
key was generated there and discarded; this file holds only the public key. So these tests run the same check a
separate machine would: nothing here can sign, and HERALD's code is not imported.
"""

import copy
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
from tie.source.loader import create_source

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "herald_export_current.json").read_text()
)
TEXT = FIXTURE["text"]
EXPORT = FIXTURE["export"]
PUB = serialization.load_pem_public_key(FIXTURE["public_key_pem"].encode())
PINNED = {export_key_id(PUB): PUB}


def _source():
    return create_source(EXPORT["document"]["source_id"], TEXT)


def test_current_herald_export_is_accepted_by_its_pinned_key():
    records = evidence_from_herald_export(_source(), EXPORT, trusted_keys=PINNED)
    assert len(records) == len(EXPORT["admitted"]) == 2


def test_an_altered_admitted_claim_is_refused_even_under_the_pinned_key():
    tampered = copy.deepcopy(EXPORT)
    tampered["admitted"][0]["confirmed_by"] = "mallory@example.com"
    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        evidence_from_herald_export(_source(), tampered, trusted_keys=PINNED)


def test_a_re_signature_by_an_unpinned_key_is_refused():
    other = Ed25519PrivateKey.generate()
    forged = copy.deepcopy(EXPORT)
    forged["key_id"] = export_key_id(other.public_key())
    forged["export_mac"] = other.sign(export_signing_bytes(forged)).hex()
    with pytest.raises(HeraldIntakeRefused, match="not trusted"):
        evidence_from_herald_export(_source(), forged, trusted_keys=PINNED)
