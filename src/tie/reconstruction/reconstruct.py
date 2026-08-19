from __future__ import annotations

from tie.models import EvidenceRecord, EpistemicStatus, Provenance, Reconstruction


def reconstruct_summary(*, reconstruction_id: str, evidence: tuple[EvidenceRecord, ...], provenance: Provenance) -> Reconstruction:
    if not evidence:
        return Reconstruction(
            reconstruction_id=reconstruction_id,
            text="No source-grounded evidence was available for reconstruction.",
            evidence_ids=(),
            epistemic_status=EpistemicStatus.UNKNOWN,
            provenance=provenance,
        )
    ordered = list(evidence)
    conflict = any(e.epistemic_status is EpistemicStatus.CONFLICTED for e in ordered)
    inferred = any(e.epistemic_status is EpistemicStatus.INFERRED for e in ordered)
    status = EpistemicStatus.CONFLICTED if conflict else (EpistemicStatus.INFERRED if inferred else EpistemicStatus.EXPLICIT)
    text = "\n".join(f"- {e.statement}" for e in ordered)
    return Reconstruction(
        reconstruction_id=reconstruction_id,
        text=text,
        evidence_ids=tuple(e.evidence_id for e in ordered),
        epistemic_status=status,
        provenance=provenance,
        conflict_notes=("Contains at least one conflicted evidence record.",) if conflict else (),
    )
