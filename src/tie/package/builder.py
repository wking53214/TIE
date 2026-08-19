from __future__ import annotations

from tie.models import Provenance, TIEPackage, TypedHandoff, BuildClassification
from tie.validation import validate_package


def build_package(*, package_id: str, source, coverage, evidence=(), artifacts=(), identity_references=(), relationships=(), reconstruction=None, knowledge_views=None, routing_signal=None, objective="Provide source-grounded transcript intelligence to downstream Gems.") -> TIEPackage:
    handoff = TypedHandoff(
        objective=objective,
        source_id=source.source_id,
        evidence_ids=tuple(e.evidence_id for e in evidence),
        artifact_ids=tuple(a.artifact_id for a in artifacts),
        known_uncertainty=tuple(
            e.evidence_id for e in evidence if e.epistemic_status.value in {"UNKNOWN", "CONFLICTED"}
        ),
        routing_signal=routing_signal,
        provenance=source.provenance,
    )
    pkg = TIEPackage(
        package_id=package_id,
        source=source,
        coverage=coverage,
        evidence=tuple(evidence),
        artifacts=tuple(artifacts),
        identity_references=tuple(identity_references),
        relationships=tuple(relationships),
        reconstruction=reconstruction,
        knowledge_views=knowledge_views or {},
        typed_handoff=handoff,
        routing_signal=routing_signal,
        build_classification=BuildClassification.IMPLEMENTED_FROM_RECOVERED_SPEC,
    )
    return TIEPackage(**{**pkg.__dict__, "validation": validate_package(pkg)})
