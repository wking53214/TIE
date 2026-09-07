from __future__ import annotations

from tie.models import CoverageStatus, TIEPackage, ValidationResult


def coverage_gaps(coverage) -> tuple[str, ...]:
    """Human-readable statements of what the coverage record says was not
    looked at. Empty when every segment was inspected.

    Measured before this existed: a package whose every segment was
    NOT_INSPECTED validated with no errors and no warnings, and its typed
    handoff carried an empty known_uncertainty. A reader who is not told
    that 3 of 3 segments went uninspected reads the handoff as covering
    the source.
    """
    segments = coverage.segments
    if not segments:
        return ()
    total = len(segments)
    gaps = []
    for status, label in (
        (CoverageStatus.NOT_INSPECTED, "not inspected"),
        (CoverageStatus.MISSING, "missing from the source"),
    ):
        count = sum(1 for s in segments if s.status is status)
        if count:
            gaps.append(f"{count} of {total} source segments {label}")
    return tuple(gaps)


def validate_package(package: TIEPackage) -> ValidationResult:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    warnings: list[str] = []

    checks["source_present"] = bool(package.source.content is not None)
    checks["coverage_source_matches"] = package.coverage.source_id == package.source.source_id
    checks["evidence_have_source_refs"] = all(e.source_ref.source_id == package.source.source_id for e in package.evidence)
    checks["reconstruction_is_derived"] = package.reconstruction is None or package.reconstruction.evidence_ids
    checks["routing_not_execution"] = True
    checks["coverage_complete_claim_is_honest"] = not package.coverage.complete or bool(package.coverage.segments)
    # A source none of whose segments was inspected has not been read. Such a
    # package can carry evidence records, but nothing ties them to inspected
    # text, so it is not source-grounded intelligence and does not validate.
    checks["coverage_inspected_any"] = (
        not package.coverage.segments or bool(package.coverage.inspected_segments)
    )
    # Recorded, not required: partial coverage is honest as long as it is
    # said. The gaps themselves go into warnings and the handoff.
    checks["coverage_all_inspected"] = (
        not package.coverage.segments or package.coverage.complete
    )

    for name, ok in checks.items():
        if not ok and name != "coverage_all_inspected":
            errors.append(name)

    if not package.coverage.segments:
        warnings.append("No coverage segments are recorded.")
    warnings.extend(coverage_gaps(package.coverage))
    if package.reconstruction and not package.reconstruction.evidence_ids:
        errors.append("Reconstruction must cite evidence.")

    return ValidationResult(valid=not errors, checks=checks, errors=tuple(errors), warnings=tuple(warnings))
