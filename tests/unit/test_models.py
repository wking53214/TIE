from tie.models import EpistemicStatus, OriginKind, Provenance, SourceRef, SourceRecord


def test_epistemic_status_is_not_confidence():
    assert EpistemicStatus.EXPLICIT.value == "EXPLICIT"
    assert EpistemicStatus.CONFLICTED.value == "CONFLICTED"


def test_source_is_immutable_dataclass():
    source = SourceRecord(source_id="s1", content="original", provenance=Provenance(origin=OriginKind.HUMAN))
    assert source.content == "original"


def test_source_ref_can_locate_segment():
    ref = SourceRef(source_id="s1", message_id="m2", segment_id="s1:seg:0001")
    assert ref.segment_id == "s1:seg:0001"
