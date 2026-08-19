from tie import EpistemicStatus, Provenance, create_source, evidence_from_statement, segment_source, build_package


def test_conflicted_evidence_remains_conflicted():
    source = create_source("s", "A. B.")
    coverage = segment_source(source, max_chars=10)
    e = evidence_from_statement(
        source,
        evidence_id="e-conflict",
        statement="A and B conflict.",
        epistemic_status=EpistemicStatus.CONFLICTED,
        segment_id=coverage.segments[0].segment_id,
    )
    package = build_package(package_id="p", source=source, coverage=coverage, evidence=(e,))
    assert package.evidence[0].epistemic_status is EpistemicStatus.CONFLICTED
    assert "e-conflict" in package.typed_handoff.known_uncertainty


def test_routing_signal_is_data_only():
    source = create_source("s", "text")
    coverage = segment_source(source)
    package = build_package(package_id="p", source=source, coverage=coverage, routing_signal="review")
    assert package.routing_signal == "review"
