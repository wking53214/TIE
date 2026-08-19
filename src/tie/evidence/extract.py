from __future__ import annotations

from tie.models import EvidenceRecord, EpistemicStatus, Provenance, SourceRecord, SourceRef


def evidence_from_statement(
    source: SourceRecord,
    *,
    evidence_id: str,
    statement: str,
    epistemic_status: EpistemicStatus,
    segment_id: str | None = None,
) -> EvidenceRecord:
    if not statement.strip():
        raise ValueError("statement must not be empty")
    source_ref = source.provenance.source or SourceRef(source_id=source.source_id, segment_id=segment_id)
    if segment_id is not None and source_ref.segment_id != segment_id:
        source_ref = SourceRef(
            source_id=source_ref.source_id,
            source_location=source_ref.source_location,
            conversation_id=source_ref.conversation_id,
            message_id=source_ref.message_id,
            segment_id=segment_id,
        )
    return EvidenceRecord(
        evidence_id=evidence_id,
        statement=statement,
        epistemic_status=epistemic_status,
        source_ref=source_ref,
        provenance=source.provenance,
        segment_id=segment_id,
    )
