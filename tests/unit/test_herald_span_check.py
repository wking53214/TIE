"""A claim's quoted text must be what the source holds at its declared span.

HERALD's convention (its own seal check): `span` is [start, end) in characters into the exact source text, with no
normalization, and `raw` is exactly text[start:end]. A valid signature and a matching document hash are not enough."""

import copy
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tie.evidence.herald_intake import (
    HeraldIntakeRefused,
    evidence_from_herald_export,
    export_key_id,
    export_signing_bytes,
    signoffs_from_herald_export,
)
from tie.source.loader import create_source

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "herald_export_v4.json").read_text())
TEXT = FIXTURE["text"]
EXPORT = FIXTURE["export"]
PUB = serialization.load_pem_public_key(FIXTURE["public_key_pem"].encode())
PINNED = {export_key_id(PUB): PUB}
NOW = datetime.fromisoformat(EXPORT["identity"]["signed_at"]) + timedelta(seconds=30)

_KEY = Ed25519PrivateKey.generate()
_KEY_PINNED = {export_key_id(_KEY.public_key()): _KEY.public_key()}


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _signed(export):
    export = copy.deepcopy(export)
    export["key_id"] = export_key_id(_KEY.public_key())
    export["export_mac"] = _KEY.sign(export_signing_bytes(export)).hex()
    return export


def _export_over(text, *spans_and_raws):
    """A correctly signed export of hand-picked claims over `text`, so each test controls exactly what is quoted."""
    export = copy.deepcopy(EXPORT)
    base = export["admitted"][0]
    export["admitted"] = []
    for i, (span, raw) in enumerate(spans_and_raws):
        entry = copy.deepcopy(base)
        entry.update({"claim_id": f"clm-test-{i}", "span": span, "raw": raw, "source_hash": _sha(text)})
        export["admitted"].append(entry)
    return _signed(export)


def _take(text, export):
    return evidence_from_herald_export(
        create_source("doc-1", text), export, trusted_keys=_KEY_PINNED, now=NOW)


def _mutated(**changes):
    export = copy.deepcopy(EXPORT)
    export["admitted"][0].update(changes)
    return _signed(export)


def test_the_genuine_export_still_passes_both_paths():
    source = create_source(EXPORT["document"]["source_id"], TEXT)
    assert evidence_from_herald_export(source, EXPORT, trusted_keys=PINNED, now=NOW)
    signoffs_from_herald_export(source, EXPORT, trusted_keys=PINNED, now=NOW)


@pytest.mark.parametrize("changes", [
    {"span": [19, 29]},                 # shifted by one: the slice is no longer the quote
    {"raw": "$9,999.00 "},              # fabricated quote at the real position
    {"raw": "$1,250.00"},               # one character short: no normalization is applied
    {"span": [18, 18], "raw": ""},      # empty span quotes nothing
    {"span": [28, 18]},                 # end before start
    {"span": [-1, 9]},                  # negative start
    {"span": [18, 10_000]},             # past the end of the text
    {"span": [18]},                     # wrong length
    {"span": [18, 28, 30]},             # wrong length
    {"span": ["18", "28"]},             # not integers
    {"span": [18.0, 28.0]},             # floats are not offsets
    {"span": [True, 28]},               # a boolean is not an offset
    {"span": None},
    {"span": "18-28"},
    {"raw": None},
    {"raw": 5},
])
def test_an_inconsistent_claim_is_refused_on_both_paths(changes):
    export = _mutated(**changes)
    source = create_source(EXPORT["document"]["source_id"], TEXT)
    with pytest.raises(HeraldIntakeRefused):
        evidence_from_herald_export(source, export, trusted_keys=_KEY_PINNED, now=NOW)
    with pytest.raises(HeraldIntakeRefused):
        signoffs_from_herald_export(source, export, trusted_keys=_KEY_PINNED, now=NOW)


def test_a_missing_span_or_quote_is_refused():
    for field in ("span", "raw"):
        export = copy.deepcopy(EXPORT)
        del export["admitted"][0][field]
        with pytest.raises(HeraldIntakeRefused):
            _take(TEXT, _signed(export))


def test_one_bad_entry_refuses_the_whole_export():
    """No partial admission: a good first claim does not rescue a fabricated second one."""
    good = (list(EXPORT["admitted"][0]["span"]), EXPORT["admitted"][0]["raw"])
    export = _export_over(TEXT, good, ([31, 41], "2026-03-15"))
    with pytest.raises(HeraldIntakeRefused, match="not at its declared span"):
        _take(TEXT, export)


def test_offsets_count_characters_not_bytes():
    text = "Café \U0001F600 paid $500 today."
    start = text.index("$500")
    quoted = text[start:start + 4]
    assert _take(text, _export_over(text, ([start, start + 4], quoted)))
    byte_start = len(text[:start].encode("utf-8"))  # what a byte-offset reader would claim
    assert byte_start != start
    with pytest.raises(HeraldIntakeRefused):
        _take(text, _export_over(text, ([byte_start, byte_start + 4], quoted)))


def test_overlapping_claims_are_allowed():
    """The same stretch of text can honestly yield two kinds; overlap alone is not an inconsistency."""
    text = "Ticket TKT-9921 was closed."
    records = _take(text, _export_over(text, ([7, 15], "TKT-9921"), ([7, 11], "TKT-")))
    assert len(records) == 2 and records[0].evidence_id != records[1].evidence_id
