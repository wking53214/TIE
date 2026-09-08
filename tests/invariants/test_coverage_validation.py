"""Validation is not blind to coverage.

Measured before this existed: a package whose every coverage segment was
NOT_INSPECTED validated with no errors and no warnings, and its typed
handoff carried an empty known_uncertainty.
"""

import dataclasses

from tie import EpistemicStatus, OriginKind, Provenance, build_package, create_source, evidence_from_statement, segment_source
from tie.models import CoverageStatus


def _package(statuses):
    source = create_source("src-1", "First statement. Second statement. Third statement.",
                           provenance=Provenance(origin=OriginKind.AI))
    coverage = segment_source(source, max_chars=18)
    assert len(coverage.segments) == len(statuses)
    segments = tuple(dataclasses.replace(s, status=st) for s, st in zip(coverage.segments, statuses))
    coverage = dataclasses.replace(coverage, segments=segments)
    evidence = evidence_from_statement(
        source, evidence_id="ev-1", statement="First statement.",
        epistemic_status=EpistemicStatus.EXPLICIT, segment_id=coverage.segments[0].segment_id,
    )
    return build_package(package_id="p1", source=source, coverage=coverage,
                         evidence=(evidence,), routing_signal="knowledge-review")


INS, NOT, MISS = CoverageStatus.INSPECTED, CoverageStatus.NOT_INSPECTED, CoverageStatus.MISSING


def test_fully_inspected_coverage_is_clean():
    pkg = _package([INS, INS, INS])
    assert pkg.validation.valid
    assert pkg.validation.warnings == ()
    assert pkg.validation.checks["coverage_all_inspected"] is True
    assert pkg.typed_handoff.known_uncertainty == ()


def test_nothing_inspected_does_not_validate():
    pkg = _package([NOT, NOT, NOT])
    assert pkg.validation.valid is False
    assert "coverage_inspected_any" in pkg.validation.errors
    assert "3 of 3 source segments not inspected" in pkg.validation.warnings
    assert "3 of 3 source segments not inspected" in pkg.typed_handoff.known_uncertainty


def test_partial_coverage_validates_but_is_said_everywhere():
    pkg = _package([INS, NOT, MISS])
    assert pkg.validation.valid is True
    assert pkg.validation.checks["coverage_all_inspected"] is False
    assert "coverage_all_inspected" not in pkg.validation.errors
    assert "1 of 3 source segments not inspected" in pkg.validation.warnings
    assert "1 of 3 source segments missing from the source" in pkg.validation.warnings
    assert "1 of 3 source segments not inspected" in pkg.typed_handoff.known_uncertainty
    assert "1 of 3 source segments missing from the source" in pkg.typed_handoff.known_uncertainty


def test_coverage_gaps_sit_beside_evidence_uncertainty_not_instead_of_it():
    source = create_source("src-2", "Something uncertain was said here.",
                           provenance=Provenance(origin=OriginKind.AI))
    coverage = segment_source(source, max_chars=10)
    segments = (dataclasses.replace(coverage.segments[0], status=NOT),) + coverage.segments[1:]
    coverage = dataclasses.replace(coverage, segments=segments)
    conflicted = evidence_from_statement(
        source, evidence_id="e-conflict", statement="Something uncertain",
        epistemic_status=EpistemicStatus.CONFLICTED, segment_id=coverage.segments[1].segment_id,
    )
    pkg = build_package(package_id="p2", source=source, coverage=coverage, evidence=(conflicted,))
    assert "e-conflict" in pkg.typed_handoff.known_uncertainty
    assert any(u.endswith("not inspected") for u in pkg.typed_handoff.known_uncertainty)
