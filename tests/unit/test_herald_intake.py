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


@pytest.mark.parametrize("reading", ["HUMAN_CONFIRMED", "WEIRD", None])
def test_only_machine_readings_enter(reading):
    export = json.loads(json.dumps(EXPORT))
    export["admitted"][0]["reading"] = reading
    assert evidence_from_herald_export(_source(), export, verify=_accept) == []


def test_replaying_the_same_export_gives_the_same_evidence_ids():
    first = evidence_from_herald_export(_source(), EXPORT, verify=_accept)
    second = evidence_from_herald_export(_source(), EXPORT, verify=_accept)
    assert [r.evidence_id for r in first] == [r.evidence_id for r in second]


def test_same_claim_at_a_different_span_gets_a_different_id():
    moved = json.loads(json.dumps(EXPORT))
    moved["admitted"][0]["span"] = [moved["admitted"][0]["span"][0] + 1, moved["admitted"][0]["span"][1] + 1]
    original = evidence_from_herald_export(_source(), EXPORT, verify=_accept)[0].evidence_id
    shifted = evidence_from_herald_export(_source(), moved, verify=_accept)[0].evidence_id
    assert original != shifted


def test_refused_claims_never_enter():
    assert EXPORT["refused"], "fixture should include a refused claim"
    records = evidence_from_herald_export(_source(), EXPORT, verify=_accept)
    refused_ids = {f"herald-{r['claim_id']}" for r in EXPORT["refused"]}
    assert not refused_ids & {r.evidence_id for r in records}


def test_a_claim_from_different_text_is_refused():
    other = create_source("inv-1", TEXT + " Extra sentence changes the hash.")
    with pytest.raises(HeraldIntakeRefused, match="different text"):
        evidence_from_herald_export(other, EXPORT, verify=_accept)
