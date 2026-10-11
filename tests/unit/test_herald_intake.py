"""HERALD intake: admitted claims become TIE evidence, and nothing else does.

The fixture is a real HERALD export (tests/fixtures/herald_export.json).
"""

import json
from pathlib import Path

import pytest

from tie.evidence.herald_intake import HeraldIntakeRefused, evidence_from_herald_export
from tie.models import EpistemicStatus
from tie.source.loader import create_source

FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "herald_export.json").read_text()
)
TEXT = FIXTURE["text"]
EXPORT = FIXTURE["export"]


def _source():
    return create_source("inv-1", TEXT)


def _accept(_export):
    return None


def test_refuses_without_a_verifier():
    with pytest.raises(HeraldIntakeRefused, match="no export verifier"):
        evidence_from_herald_export(_source(), EXPORT)


def test_refuses_when_the_verifier_rejects_the_export():
    def reject(_export):
        raise ValueError("bad MAC")

    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        evidence_from_herald_export(_source(), EXPORT, verify=reject)


def test_admitted_claims_become_inferred_evidence():
    records = evidence_from_herald_export(_source(), EXPORT, verify=_accept)
    assert len(records) == len(EXPORT["admitted"]) == 1
    record = records[0]
    assert record.epistemic_status is EpistemicStatus.INFERRED
    assert record.evidence_id.startswith("herald-")
    assert EXPORT["admitted"][0]["raw"] in record.statement


def test_refused_claims_never_enter():
    assert EXPORT["refused"], "fixture should include a refused claim"
    records = evidence_from_herald_export(_source(), EXPORT, verify=_accept)
    refused_ids = {f"herald-{r['claim_id']}" for r in EXPORT["refused"]}
    assert not refused_ids & {r.evidence_id for r in records}


def test_a_claim_from_different_text_is_refused():
    other = create_source("inv-1", TEXT + " Extra sentence changes the hash.")
    with pytest.raises(HeraldIntakeRefused, match="different text"):
        evidence_from_herald_export(other, EXPORT, verify=_accept)
