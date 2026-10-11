"""Intake for HERALD claims: admitted HERALD claims become TIE evidence.

HERALD extracts candidate claims from a document. TIE records evidence and
does not guess what a statement means. This module puts HERALD's admitted
claims into TIE's evidence record. Each claim keeps its source id, segment,
and text hash, and is recorded as INFERRED, because extraction is
interpretation.

Rules, all fail closed:
- Refused claims never enter. Refused claims wait for a named human.
- Only machine readings (EXTRACTED, INFERRED) enter. A HUMAN_CONFIRMED claim
  is a person's sign-off and needs its own evidence path, not this one. Any
  unknown reading is also left out.
- Evidence IDs are derived from the claim's source hash, kind, span and text,
  so re-ingesting the same export produces the same IDs instead of duplicates.
- The HERALD export must pass a verifier the caller supplies. Without one,
  intake refuses. HERALD's export MAC is keyed to its own process, so a
  consumer in another process cannot check it alone.
- Every admitted claim must match the source text by hash. A claim read from
  different text is refused.

TIE imports nothing from HERALD. The export is read by key.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, List, Mapping, Optional

from tie.evidence.extract import evidence_from_statement
from tie.models import EpistemicStatus, EvidenceRecord, SourceRecord

__all__ = ["HeraldIntakeRefused", "evidence_from_herald_export", "MACHINE_READINGS"]

#: HERALD readings that are machine output. HUMAN_CONFIRMED is absent on purpose.
MACHINE_READINGS = frozenset({"EXTRACTED", "INFERRED"})


class HeraldIntakeRefused(ValueError):
    """Raised when a HERALD export cannot be taken in as TIE evidence."""


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _evidence_id(source_hash: str, entry: Mapping[str, Any]) -> str:
    """Deterministic: the same claim read from the same text gets the same ID.

    HERALD's claim_id is random per run, so using it would make every replay
    of the same export look like new evidence.
    """
    start, end = entry["span"]
    key = "|".join([source_hash, str(entry["kind"]), str(start), str(end), str(entry["raw"])])
    return "herald-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def evidence_from_herald_export(
    source: SourceRecord,
    export: Mapping[str, Any],
    *,
    verify: Optional[Callable[[Mapping[str, Any]], None]] = None,
) -> List[EvidenceRecord]:
    """Turn the admitted claims of a HERALD export into TIE evidence records.

    ``verify`` is called with the export and must raise if it is not genuine.
    Pass HERALD's own ``verify_export`` from the process that issued it.
    """
    if verify is None:
        raise HeraldIntakeRefused(
            "no export verifier supplied; refusing unverified HERALD output"
        )
    try:
        verify(export)
    except Exception as exc:  # any failure to verify is a refusal
        raise HeraldIntakeRefused(f"HERALD export did not verify: {exc}") from exc

    expected_hash = _text_hash(source.content)
    records: List[EvidenceRecord] = []
    for entry in export.get("admitted", []):
        if entry.get("source_hash") != expected_hash:
            raise HeraldIntakeRefused(
                f"claim {entry.get('claim_id')!r} was read from different text "
                "than the source it was offered with"
            )
        if entry.get("reading") not in MACHINE_READINGS:
            # A person's sign-off, or an unknown reading: not evidence this path takes.
            continue
        statement = f"{entry['kind']}: {entry['raw']}"
        records.append(
            evidence_from_statement(
                source,
                evidence_id=_evidence_id(expected_hash, entry),
                statement=statement,
                epistemic_status=EpistemicStatus.INFERRED,
                segment_id=entry.get("segment"),
            )
        )
    return records
