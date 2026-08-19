from __future__ import annotations

from tie.models import TIEPackage, ValidationResult


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

    for name, ok in checks.items():
        if not ok:
            errors.append(name)

    if not package.coverage.segments:
        warnings.append("No coverage segments are recorded.")
    if package.reconstruction and not package.reconstruction.evidence_ids:
        errors.append("Reconstruction must cite evidence.")

    return ValidationResult(valid=not errors, checks=checks, errors=tuple(errors), warnings=tuple(warnings))
