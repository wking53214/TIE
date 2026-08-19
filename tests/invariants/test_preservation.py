from tie import create_source, segment_source


def test_segmentation_does_not_change_source_text():
    text = "abcdefghij"
    source = create_source("s1", text)
    coverage = segment_source(source, max_chars=4)
    reconstructed = "".join(text[s.start_char:s.end_char] for s in coverage.segments)
    assert reconstructed == text
    assert source.content == text


def test_incomplete_coverage_is_visible():
    source = create_source("s1", "abcdef")
    coverage = segment_source(source, max_chars=3)
    assert coverage.complete is True
    from tie.models import CoverageStatus, CoverageSegment, Coverage
    partial = Coverage(source_id="s1", segments=(CoverageSegment("s", 0, 0, 3, CoverageStatus.INSPECTED, "s1"), CoverageSegment("x", 1, 3, 6, CoverageStatus.NOT_INSPECTED, "s1")))
    assert partial.complete is False
