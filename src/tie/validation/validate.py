from __future__ import annotations

import re

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


# A routing signal is a short label that names where a package is meant to be looked at next. Letters, digits, dot,
# underscore and hyphen, starting with a letter, at most 64 characters. No spaces, punctuation or line breaks, so a
# sentence, a command line or a multi-line instruction cannot be carried in it. TIE cannot tell what a label MEANS
# (a label that happens to be a verb still passes); it enforces the shape and the consistency below, and nothing in
# TIE reads the signal to act on it (tests/invariants/test_routing_validation.py checks that too).
ROUTING_LABEL = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}")


def routing_is_data_only(pkg: TIEPackage) -> bool:
    """True when the package's routing is plain data: a label or nothing, the same on the package and its handoff.

    It fails for a signal that is not a label (so it cannot read as an instruction), and for a package and typed
    handoff that disagree about the signal (contradictory routing). It never grants anything: passing means "this is
    data", not "this may run"."""
    signals = [pkg.routing_signal]
    if pkg.typed_handoff is not None:
        if pkg.typed_handoff.routing_signal != pkg.routing_signal:
            return False
        signals.append(pkg.typed_handoff.routing_signal)
    return all(s is None or (isinstance(s, str) and ROUTING_LABEL.fullmatch(s) is not None) for s in signals)


def validate_package(pkg: TIEPackage) -> ValidationResult:
    checks: dict[str, bool] = {}
    errors: list[str] = []
    warnings: list[str] = []

    checks["source_present"] = bool(pkg.source.content is not None)
    checks["coverage_source_matches"] = pkg.coverage.source_id == pkg.source.source_id
    checks["evidence_have_source_refs"] = all(e.source_ref.source_id == pkg.source.source_id for e in pkg.evidence)
    checks["reconstruction_is_derived"] = pkg.reconstruction is None or pkg.reconstruction.evidence_ids
    checks["routing_not_execution"] = routing_is_data_only(pkg)
    checks["coverage_complete_claim_is_honest"] = not pkg.coverage.complete or bool(pkg.coverage.segments)
    # A source none of whose segments was inspected has not been read. Such a
    # package can carry evidence records, but nothing ties them to inspected
    # text, so it is not source-grounded intelligence and does not validate.
    checks["coverage_inspected_any"] = (
        not pkg.coverage.segments or bool(pkg.coverage.inspected_segments)
    )
    # Recorded, not required: partial coverage is honest as long as it is
    # said. The gaps themselves go into warnings and the handoff.
    checks["coverage_all_inspected"] = (
        not pkg.coverage.segments or pkg.coverage.complete
    )

    for name, ok in checks.items():
        if not ok and name != "coverage_all_inspected":
            errors.append(name)

    if not pkg.coverage.segments:
        warnings.append("No coverage segments are recorded.")
    warnings.extend(coverage_gaps(pkg.coverage))
    if pkg.reconstruction and not pkg.reconstruction.evidence_ids:
        errors.append("Reconstruction must cite evidence.")

    return ValidationResult(valid=not errors, checks=checks, errors=tuple(errors), warnings=tuple(warnings))
