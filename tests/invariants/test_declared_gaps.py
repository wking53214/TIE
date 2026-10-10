"""Coverage can say "not read".

Before this, segment_source marked every segment INSPECTED, so NOT_INSPECTED
and MISSING could only appear if a caller edited the record by hand. A source
that was truncated or only partly examined looked fully covered.
"""

import pytest

from tie import EpistemicStatus, OriginKind, Provenance, build_package, create_source, evidence_from_statement, segment_source
from tie.models import CoverageStatus

INS, NOT, MISS = CoverageStatus.INSPECTED, CoverageStatus.NOT_INSPECTED, CoverageStatus.MISSING
TEXT = "First statement. Second statement. Third statement."  # 51 chars


def _src(text=TEXT):
    return create_source("src-1", text, provenance=Provenance(origin=OriginKind.AI))


def _statuses(cov):
    return [s.status for s in cov.segments]


def test_default_is_unchanged_every_segment_inspected():
    cov = segment_source(_src(), max_chars=18)
    assert _statuses(cov) == [INS, INS, INS]
    assert cov.complete


def test_a_range_the_caller_did_not_read_marks_the_segments_it_touches():
    # Characters 20..30 sit inside the second 18-char segment only.
    cov = segment_source(_src(), max_chars=18, not_inspected=[(20, 30)])
    assert _statuses(cov) == [INS, NOT, INS]
    assert not cov.complete
    assert cov.segments[1].notes


def test_a_partly_read_segment_counts_as_not_inspected():
    cov = segment_source(_src(), max_chars=18, not_inspected=[(17, 19)])
    assert _statuses(cov) == [NOT, NOT, INS]


def test_a_range_ending_exactly_at_a_boundary_does_not_touch_the_next_segment():
    cov = segment_source(_src(), max_chars=18, not_inspected=[(0, 18)])
    assert _statuses(cov) == [NOT, INS, INS]


def test_truncated_content_is_recorded_as_missing_with_no_checksum():
    src = _src(TEXT[:36])
    cov = segment_source(src, max_chars=18, declared_length=len(TEXT))
    assert _statuses(cov) == [INS, INS, MISS]
    missing = cov.segments[2]
    assert (missing.start_char, missing.end_char) == (36, len(TEXT))
    assert missing.checksum is None


def test_missing_tail_is_chunked_like_the_rest_and_ordinals_continue():
    cov = segment_source(_src("abc"), max_chars=4, declared_length=11)
    assert _statuses(cov) == [INS, MISS, MISS]
    assert [s.ordinal for s in cov.segments] == [0, 1, 2]
    assert [(s.start_char, s.end_char) for s in cov.segments[1:]] == [(3, 7), (7, 11)]


def test_nothing_read_but_something_declared_is_all_missing():
    cov = segment_source(_src(""), max_chars=5, declared_length=7)
    assert _statuses(cov) == [MISS, MISS]


def test_declared_length_equal_to_content_changes_nothing():
    assert segment_source(_src(), max_chars=18, declared_length=len(TEXT)) == segment_source(_src(), max_chars=18)


@pytest.mark.parametrize("bad", [(-1, 5), (5, 5), (6, 5), (0, 52)])
def test_impossible_ranges_are_refused(bad):
    with pytest.raises(ValueError):
        segment_source(_src(), max_chars=18, not_inspected=[bad])


def test_declared_length_shorter_than_content_is_refused():
    with pytest.raises(ValueError):
        segment_source(_src(), declared_length=10)


def test_the_gaps_reach_the_handoff_and_validation():
    src = _src(TEXT[:36])
    cov = segment_source(src, max_chars=18, not_inspected=[(0, 5)], declared_length=len(TEXT))
    ev = evidence_from_statement(
        src, evidence_id="ev-1", statement="Second statement.",
        epistemic_status=EpistemicStatus.EXPLICIT, segment_id=cov.segments[1].segment_id,
    )
    pkg = build_package(package_id="p", source=src, coverage=cov, evidence=(ev,))
    assert pkg.validation.valid  # partial coverage is honest as long as it is said
    said = pkg.typed_handoff.known_uncertainty
    assert "1 of 3 source segments not inspected" in said
    assert "1 of 3 source segments missing from the source" in said


def test_human_accepted_ai_is_its_own_origin():
    assert OriginKind.HUMAN_ACCEPTED_AI not in (OriginKind.HUMAN, OriginKind.AI)
    assert OriginKind("HUMAN_ACCEPTED_AI") is OriginKind.HUMAN_ACCEPTED_AI
