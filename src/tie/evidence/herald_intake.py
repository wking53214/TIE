"""Intake for HERALD claims: admitted HERALD claims become TIE evidence.

HERALD extracts candidate claims from a document. TIE records evidence and
does not guess what a statement means. This module puts HERALD's admitted
claims into TIE's evidence record. Each claim keeps its source id, segment,
and text hash, and is recorded as INFERRED, because extraction is
interpretation.

Rules, all fail closed:
- Refused claims never enter. Refused claims wait for a named human.
- Only machine readings (EXTRACTED, INFERRED) enter here. A HUMAN_CONFIRMED
  claim is a person's sign-off and takes its own path, `signoffs_from_herald_export`,
  so a person's word is never mistaken for a machine reading. Any unknown
  reading is left out of both.
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

import dataclasses
import hashlib
import json
from typing import Any, Callable, List, Mapping, Optional

from tie.evidence.extract import evidence_from_statement
from tie.models import EpistemicStatus, EvidenceRecord, OriginKind, SourceRecord

__all__ = ["HeraldIntakeRefused", "evidence_from_herald_export", "signoffs_from_herald_export",
           "MACHINE_READINGS", "SIGNOFF_READING"]

#: HERALD readings that are machine output. HUMAN_CONFIRMED is absent on purpose.
MACHINE_READINGS = frozenset({"EXTRACTED", "INFERRED"})

#: HERALD's reading for a claim a named person confirmed. Taken in by `signoffs_from_herald_export` only.
SIGNOFF_READING = "HUMAN_CONFIRMED"


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


def _verified_entries(
    source: SourceRecord,
    export: Mapping[str, Any],
    verify: Optional[Callable[[Mapping[str, Any]], None]],
) -> tuple:
    """The admitted entries of a verified export, each checked against the source text. Raises on any failure."""
    if verify is None:
        raise HeraldIntakeRefused(
            "no export verifier supplied; refusing unverified HERALD output"
        )
    try:
        verify(export)
    except Exception as exc:  # any failure to verify is a refusal
        raise HeraldIntakeRefused(f"HERALD export did not verify: {exc}") from exc

    expected_hash = _text_hash(source.content)
    entries = tuple(export.get("admitted", []))
    for entry in entries:
        if entry.get("source_hash") != expected_hash:
            raise HeraldIntakeRefused(
                f"claim {entry.get('claim_id')!r} was read from different text "
                "than the source it was offered with"
            )
    return expected_hash, entries


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
    expected_hash, entries = _verified_entries(source, export, verify)
    records: List[EvidenceRecord] = []
    for entry in entries:
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


def _signoff_id(source_hash: str, entry: Mapping[str, Any], confirmed_by: str) -> str:
    """Deterministic, and never equal to a machine reading's ID: the prefix differs and the confirmer is in the key.

    Two people confirming the same claim are two pieces of evidence, so the same claim confirmed by a
    different person gets a different ID.
    """
    start, end = entry["span"]
    key = "|".join([source_hash, str(entry["kind"]), str(start), str(end), str(entry["raw"]), confirmed_by])
    return "signoff-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def signoffs_from_herald_export(
    source: SourceRecord,
    export: Mapping[str, Any],
    *,
    verify: Optional[Callable[[Mapping[str, Any]], None]] = None,
) -> List[EvidenceRecord]:
    """Turn the claims a named person confirmed at HERALD into TIE evidence, apart from machine readings.

    Same checks as `evidence_from_herald_export`: the export must verify and every claim must have been read
    from this source text. Each record says whose word it is: its provenance origin is HUMAN_ACCEPTED_AI (a
    person reviewed and accepted machine output) and its notes carry the confirmer, the confirmed value and
    HERALD's claim ID. Its ID starts with ``signoff-``, so it can never be taken for a machine reading.

    Each record also carries why they confirmed it and when (HERALD's rationale and confirmation time). A claim
    marked HUMAN_CONFIRMED that names no one, gives no reason or gives no time is refused, not skipped: a sign-off
    nobody signed, or one with nothing behind it, is not evidence of anything, and dropping it quietly is how a
    confirmation gets lost.
    """
    expected_hash, entries = _verified_entries(source, export, verify)
    records: List[EvidenceRecord] = []
    for entry in entries:
        if entry.get("reading") != SIGNOFF_READING:
            continue
        who = entry.get("confirmed_by")
        if not isinstance(who, str) or not who.strip():
            raise HeraldIntakeRefused(
                f"claim {entry.get('claim_id')!r} is marked human-confirmed but names no one who confirmed it"
            )
        for field, label in (("confirmation_rationale", "gives no reason"), ("confirmed_at", "gives no time")):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                raise HeraldIntakeRefused(f"claim {entry.get('claim_id')!r} is human-confirmed but {label} for it")
        record = evidence_from_statement(
            source,
            evidence_id=_signoff_id(expected_hash, entry, who),
            statement=f"{entry['kind']}: {entry['raw']}",
            epistemic_status=EpistemicStatus.INFERRED,
            segment_id=entry.get("segment"),
        )
        notes = (
            f"confirmed_by: {who}",
            "confirmed_value: " + json.dumps(entry.get("value"), sort_keys=True, ensure_ascii=False),
            f"confirmed_because: {entry['confirmation_rationale']}",
            f"confirmed_at: {entry['confirmed_at']}",
            f"herald_claim_id: {entry.get('claim_id')}",
        )
        records.append(dataclasses.replace(
            record,
            provenance=dataclasses.replace(record.provenance, origin=OriginKind.HUMAN_ACCEPTED_AI),
            notes=record.notes + notes,
        ))
    return records
