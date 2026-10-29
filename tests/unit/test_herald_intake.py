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
    return export


def test_signoff_path_refuses_without_a_verifier():
    with pytest.raises(HeraldIntakeRefused, match="no export verifier"):
        signoffs_from_herald_export(_source(), _signed_off())


def test_signoff_path_refuses_when_the_verifier_rejects():
    def reject(_export):
        raise ValueError("bad MAC")

    with pytest.raises(HeraldIntakeRefused, match="did not verify"):
        signoffs_from_herald_export(_source(), _signed_off(), verify=reject)


def test_a_signoff_becomes_human_accepted_evidence_naming_the_confirmer():
    records = signoffs_from_herald_export(_source(), _signed_off(), verify=_accept)
    assert len(records) == 1
    record = records[0]
    assert record.provenance.origin is OriginKind.HUMAN_ACCEPTED_AI
    assert record.evidence_id.startswith("signoff-")
    assert "confirmed_by: alice@example.com" in record.notes
    assert any(n.startswith("confirmed_value: ") and "2026-11-01" in n for n in record.notes)
    assert f"herald_claim_id: {EXPORT['admitted'][0]['claim_id']}" in record.notes


def test_signoffs_never_come_out_of_the_machine_path_and_the_reverse():
    signed = _signed_off()
    assert evidence_from_herald_export(_source(), signed, verify=_accept) == []
    assert signoffs_from_herald_export(_source(), EXPORT, verify=_accept) == []


def test_a_signoff_that_names_no_one_is_refused_not_skipped():
    for who in (None, "", "   ", 7):
        export = _signed_off()
        export["admitted"][0]["confirmed_by"] = who
        with pytest.raises(HeraldIntakeRefused, match="names no one"):
            signoffs_from_herald_export(_source(), export, verify=_accept)


@pytest.mark.parametrize("field,why", [("confirmation_rationale", "gives no reason"), ("confirmed_at", "gives no time")])
@pytest.mark.parametrize("bad", [None, "", "  "])
def test_a_signoff_with_no_reason_or_no_time_is_refused_not_skipped(field, why, bad):
    export = _signed_off()
    export["admitted"][0][field] = bad
    with pytest.raises(HeraldIntakeRefused, match=why):
        signoffs_from_herald_export(_source(), export, verify=_accept)


def test_the_reason_and_the_time_are_recorded_on_the_evidence():
    record = signoffs_from_herald_export(_source(), _signed_off(), verify=_accept)[0]
    assert "confirmed_because: checked against the paper invoice" in record.notes
    assert "confirmed_at: 2026-10-29T12:00:00+00:00" in record.notes


def test_a_signoff_missing_the_confirmer_key_is_refused():
    export = _signed_off()
    del export["admitted"][0]["confirmed_by"]
    with pytest.raises(HeraldIntakeRefused, match="names no one"):
        signoffs_from_herald_export(_source(), export, verify=_accept)


def test_a_signoff_from_different_text_is_refused():
    with pytest.raises(HeraldIntakeRefused, match="different text"):
        signoffs_from_herald_export(create_source("inv-1", TEXT + " edited"), _signed_off(), verify=_accept)


def test_two_people_confirming_the_same_claim_are_two_records():
    a = signoffs_from_herald_export(_source(), _signed_off("alice@example.com"), verify=_accept)[0]
    b = signoffs_from_herald_export(_source(), _signed_off("bob@example.com"), verify=_accept)[0]
    assert a.evidence_id != b.evidence_id


def test_replaying_a_signoff_gives_the_same_id():
    first = signoffs_from_herald_export(_source(), _signed_off(), verify=_accept)
    second = signoffs_from_herald_export(_source(), _signed_off(), verify=_accept)
    assert [r.evidence_id for r in first] == [r.evidence_id for r in second]


def test_a_signoff_id_never_equals_a_machine_reading_id():
    machine = evidence_from_herald_export(_source(), EXPORT, verify=_accept)[0].evidence_id
    signed = signoffs_from_herald_export(_source(), _signed_off(), verify=_accept)[0].evidence_id
    assert machine != signed
