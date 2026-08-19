from tie import (
    EpistemicStatus,
    OriginKind,
    Provenance,
    create_source,
    evidence_from_statement,
    reconstruct_summary,
    build_package,
    segment_source,
)


def test_end_to_end_reconstructed_pipeline():
    source = create_source("src-1", "A human-authored statement.", provenance=Provenance(origin=OriginKind.HUMAN))
    coverage = segment_source(source, max_chars=100)
    evidence = evidence_from_statement(
        source,
        evidence_id="ev-1",
        statement="A human-authored statement.",
        epistemic_status=EpistemicStatus.EXPLICIT,
        segment_id=coverage.segments[0].segment_id,
    )
    reconstruction = reconstruct_summary(
        reconstruction_id="r-1",
        evidence=(evidence,),
        provenance=source.provenance,
    )
    package = build_package(
        package_id="pkg-1",
        source=source,
        coverage=coverage,
        evidence=(evidence,),
        reconstruction=reconstruction,
        routing_signal="knowledge-review",
    )
    assert package.source.content == "A human-authored statement."
    assert package.reconstruction.evidence_ids == ("ev-1",)
    assert package.validation is not None and package.validation.valid
    assert package.typed_handoff.routing_signal == "knowledge-review"
