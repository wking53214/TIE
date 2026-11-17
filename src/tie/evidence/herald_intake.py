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
- The HERALD export must be SIGNED (version 4, or the older version 3, both Ed25519) by a key in
  ``trusted_keys``, which the caller pins. TIE checks the signature itself;
  it does not accept a verifier function from the caller, because a caller
  supplied verifier is only as honest as the caller. Unsigned (version 1 or 2)
  exports are refused: their proof lives in the producing process only.
- A version 4 export also carries a signed identity: a unique handoff ID, the signer's own signing time, and the
  audience it is addressed to. TIE refuses one addressed to someone else, one signed too long ago (the default
  window is 24 hours) or too far in the future (5 minutes of clock difference is allowed), and, through
  `SeenHandoffs`, one it has already taken in. The signing time is the signer's claim, not an independent clock.
- Version 3 has none of that. It is still accepted, with a warning, until `V3_SUNSET`; after that it is refused.
- Every admitted claim must match the source text by hash. A claim read from
  different text is refused.

TIE imports nothing from HERALD. The export is read by key.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import threading
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, List, Mapping, Optional, Protocol, runtime_checkable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from tie.evidence.extract import evidence_from_statement
from tie.models import EpistemicStatus, EvidenceRecord, OriginKind, SourceRecord

__all__ = ["HeraldIntakeRefused", "evidence_from_herald_export", "signoffs_from_herald_export",
           "MACHINE_READINGS", "SIGNOFF_READING", "source_sha256_of", "SeenHandoffs", "HandoffLedger", "record_handoff_once",
           "V3_SUNSET", "DEFAULT_AUDIENCE", "DEFAULT_MAX_AGE_SECONDS"]

_log = logging.getLogger(__name__)

#: HERALD export formats TIE accepts: an Ed25519 signature by a pinned key. Version 3 has no identity block and is
#: being phased out (see V3_SUNSET); version 4 signs a handoff ID, signing time, audience and schema label.
EXPORT_SIGNATURE_VERSION = "3"
EXPORT_SIGNATURE_VERSION_V4 = "4"
EXPORT_SCHEMA_V4 = "herald-handoff/4"
_ACCEPTED_VERSIONS = (EXPORT_SIGNATURE_VERSION, EXPORT_SIGNATURE_VERSION_V4)

#: After this moment a version 3 export is refused. Before it, accepted with a warning.
V3_SUNSET = datetime(2027, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
#: Who this receiver is. A version 4 export addressed to anyone else is refused.
DEFAULT_AUDIENCE = "TIE"
#: How old a version 4 export's signing time may be. A choice for the deployer, not a security constant.
DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60
#: How far in the future a signing time may be, to allow for two clocks that disagree a little.
_CLOCK_SKEW = timedelta(minutes=5)

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


def export_key_id(public_key: Ed25519PublicKey) -> str:
    """The label HERALD names its export key by. Must match herald.handoff.export_key_id exactly."""
    from cryptography.hazmat.primitives import serialization

    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return "ed25519-" + hashlib.sha256(raw).hexdigest()[:16]


def export_signing_bytes(export: Mapping[str, Any]) -> bytes:
    """The exact bytes HERALD's signature covers (version 3, or version 4 with its identity block).

    Must match herald.handoff._signature_input byte for byte. The shared vectors are in tests/unit/test_herald_intake.py
    and the same vectors are asserted in HERALD's tests, so a drift on either side is a red test.
    """
    version = EXPORT_SIGNATURE_VERSION_V4 if export.get("export_mac_version") == EXPORT_SIGNATURE_VERSION_V4 \
        else EXPORT_SIGNATURE_VERSION
    payload = {
        "export_mac_version": version,
        "document": export.get("document") or {},
        "herald": export.get("herald") or {},
        "admitted": export.get("admitted") or [],
        "refused": export.get("refused") or [],
        "key_id": export.get("key_id"),
    }
    if version == EXPORT_SIGNATURE_VERSION_V4:
        payload["identity"] = export.get("identity") or {}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _check_signature(export: Mapping[str, Any], trusted_keys: Mapping[str, Ed25519PublicKey]) -> None:
    if export.get("export_mac_version") not in _ACCEPTED_VERSIONS:
        raise HeraldIntakeRefused(
            "only signed HERALD exports (version 3 or 4) are accepted; an unsigned or in-process export is refused"
        )
    key_id = export.get("key_id")
    key = trusted_keys.get(key_id) if isinstance(key_id, str) else None
    if key is None:
        raise HeraldIntakeRefused(f"HERALD export was signed with key {key_id!r}, which is not trusted here")
    claimed = export.get("export_mac")
    if not isinstance(claimed, str):
        raise HeraldIntakeRefused("HERALD export has no signature")
    try:
        key.verify(bytes.fromhex(claimed), export_signing_bytes(export))
    except (InvalidSignature, ValueError) as exc:
        raise HeraldIntakeRefused(f"HERALD export did not verify: signature does not match ({type(exc).__name__})") from exc


def _parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise HeraldIntakeRefused(f"HERALD export's signing time {value!r} is not a time") from exc
    if parsed.tzinfo is None:
        raise HeraldIntakeRefused("HERALD export's signing time has no time zone")
    return parsed


def _check_identity(export: Mapping[str, Any], audience: str, max_age_seconds: int,
                    now: Optional[datetime]) -> None:
    """Version 4: the identity block is signed, so these values are the signer's. Refuse what is not for us or stale.

    Version 3 has no identity block: accepted with a warning until V3_SUNSET, refused after it."""
    moment = now or datetime.now(timezone.utc)
    if export.get("export_mac_version") != EXPORT_SIGNATURE_VERSION_V4:
        if moment > V3_SUNSET:
            raise HeraldIntakeRefused(
                f"version 3 HERALD exports are no longer accepted (sunset {V3_SUNSET.date()}); "
                "ask the producer for a version 4 export"
            )
        _log.warning("HERALD version 3 export accepted without audience, signing time or handoff ID; "
                     "version 3 is refused after %s", V3_SUNSET.date())
        return
    identity = export.get("identity")
    if not isinstance(identity, Mapping):
        raise HeraldIntakeRefused("HERALD version 4 export has no identity block")
    for name in ("handoff_id", "signed_at", "audience", "schema"):
        value = identity.get(name)
        if not isinstance(value, str) or not value.strip():
            raise HeraldIntakeRefused(f"HERALD version 4 export's identity block has no {name}")
    if identity["schema"] != EXPORT_SCHEMA_V4:
        raise HeraldIntakeRefused(f"unsupported HERALD export schema {identity['schema']!r}")
    if identity["audience"] != audience:
        raise HeraldIntakeRefused(
            f"HERALD export is addressed to {identity['audience']!r}, not to {audience!r}")
    signed_at = _parse_time(identity["signed_at"])
    if signed_at > moment + _CLOCK_SKEW:
        raise HeraldIntakeRefused("HERALD export claims to be signed in the future")
    if moment - signed_at > timedelta(seconds=max_age_seconds):
        raise HeraldIntakeRefused(
            f"HERALD export was signed more than {max_age_seconds} seconds ago; ask for a fresh one")


@runtime_checkable
class HandoffLedger(Protocol):
    """What a replay ledger must offer: one atomic operation.

    `claim_once(handoff_id)` records the ID and reports whether THIS call was the first to do so: True for the first
    claim, False for every later one. The check and the record must be a single step, so two callers racing on the
    same ID can never both get True. TIE does not supply durable storage. A deployment that needs the ledger to
    survive a restart or to span several processes passes its own object (a database unique key, an exclusive file
    create) that honours this contract."""

    def claim_once(self, handoff_id: str) -> bool: ...


class SeenHandoffs:
    """The in-memory ledger. NOT DURABLE: it is empty after a restart and invisible to other processes.

    Safe against concurrent callers inside one process (a lock makes the check and the record one step). Use it for
    tests and single-process tools; a deployment that must not accept the same handoff twice across restarts passes a
    durable `HandoffLedger` instead. `has_seen` and `record` remain for older callers, but the pair is two steps and
    is not atomic; `claim_once` is the one to use."""

    def __init__(self) -> None:
        self._seen: set = set()
        self._lock = threading.Lock()

    def claim_once(self, handoff_id: str) -> bool:
        with self._lock:
            if handoff_id in self._seen:
                return False
            self._seen.add(handoff_id)
            return True

    def has_seen(self, handoff_id: str) -> bool:
        with self._lock:
            return handoff_id in self._seen

    def record(self, handoff_id: str) -> None:
        with self._lock:
            self._seen.add(handoff_id)


def record_handoff_once(export: Mapping[str, Any], seen: Any) -> None:
    """Call once per export, after it has been accepted, to claim its handoff ID. Refuses a repeat.

    YOU MUST CALL THIS. The intake functions do not record anything on their own, so without this call (and a ledger)
    replay is not detected at all. It is separate from the two intake functions because one export is normally read by
    both (machine readings and sign-offs); counting each read as a replay would refuse the second. Version 3 has no ID
    and cannot be tracked.

    `seen` is a `HandoffLedger`. If the ledger itself fails (raises, or does not return a plain True or False), the
    export is refused: TIE cannot say the ID was recorded, so it must not say the handoff was taken in.
    A legacy object with only `has_seen` and `record` still works, but those are two steps and a race can slip
    between them; it is accepted with a DeprecationWarning."""
    identity = export.get("identity")
    if export.get("export_mac_version") != EXPORT_SIGNATURE_VERSION_V4 or not isinstance(identity, Mapping):
        raise HeraldIntakeRefused("only a version 4 export has a handoff ID to track")
    handoff_id = identity.get("handoff_id")
    if not isinstance(handoff_id, str) or not handoff_id:
        raise HeraldIntakeRefused("HERALD version 4 export has no handoff ID")
    claim = getattr(seen, "claim_once", None)
    if claim is None:
        warnings.warn(
            "this ledger has no claim_once; falling back to has_seen then record, which is not atomic",
            DeprecationWarning, stacklevel=2)
        if seen.has_seen(handoff_id):
            raise HeraldIntakeRefused(f"HERALD handoff {handoff_id!r} was already taken in")
        seen.record(handoff_id)
        return
    try:
        first = claim(handoff_id)
    except Exception as exc:
        raise HeraldIntakeRefused(
            f"the replay ledger failed, so handoff {handoff_id!r} cannot be treated as taken in: {exc}") from exc
    if first is not True and first is not False:
        raise HeraldIntakeRefused("the replay ledger returned something other than True or False")
    if not first:
        raise HeraldIntakeRefused(f"HERALD handoff {handoff_id!r} was already taken in")


def _verified_entries(
    source: SourceRecord,
    export: Mapping[str, Any],
    trusted_keys: Optional[Mapping[str, Ed25519PublicKey]],
    audience: str = DEFAULT_AUDIENCE,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: Optional[datetime] = None,
) -> tuple:
    """The admitted entries of a verified export, each checked against the source text. Raises on any failure."""
    if not trusted_keys:
        raise HeraldIntakeRefused(
            "no trusted HERALD export keys supplied; refusing unverified HERALD output"
        )
    _check_signature(export, trusted_keys)
    _check_identity(export, audience, max_age_seconds, now)

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
    trusted_keys: Mapping[str, Ed25519PublicKey],
    audience: str = DEFAULT_AUDIENCE,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: Optional[datetime] = None,
) -> List[EvidenceRecord]:
    """Turn the admitted claims of a HERALD export into TIE evidence records.

    ``trusted_keys`` maps HERALD export key IDs to the Ed25519 public keys the caller pins. The export must be
    signed by one of them (see the module docstring). The caller never supplies a verifier function.
    """
    expected_hash, entries = _verified_entries(source, export, trusted_keys, audience, max_age_seconds, now)
    records: List[EvidenceRecord] = []
    for entry in entries:
        if entry.get("reading") not in MACHINE_READINGS:
            # A person's sign-off, or an unknown reading: not evidence this path takes.
            continue
        statement = f"{entry['kind']}: {entry['raw']}"
        record = evidence_from_statement(
            source,
            evidence_id=_evidence_id(expected_hash, entry),
            statement=statement,
            epistemic_status=EpistemicStatus.INFERRED,
            segment_id=entry.get("segment"),
        )
        # The source text hash TIE verified this claim against, recorded by TIE: a consumer that checks where a record
        # came from reads it here, not from anything the caller says about the text.
        records.append(dataclasses.replace(record, notes=(*record.notes, f"{_SOURCE_SHA256_PREFIX}{expected_hash}")))
    return records


_SOURCE_SHA256_PREFIX = "source_sha256: "


def source_sha256_of(record: EvidenceRecord) -> Optional[str]:
    """The source text hash TIE verified ``record`` against, or None if intake did not record one.

    This is the one place that reads the ``source_sha256: <hex>`` note, so a consumer need not parse notes. It is
    a helper and not a record field because a field would enter every digest of a record (`tie.cns_connector`
    binds every dataclass field), changing digests of records that exist today.
    """
    for note in record.notes:
        if note.startswith(_SOURCE_SHA256_PREFIX):
            return note[len(_SOURCE_SHA256_PREFIX):]
    return None


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
    trusted_keys: Mapping[str, Ed25519PublicKey],
    audience: str = DEFAULT_AUDIENCE,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: Optional[datetime] = None,
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
    expected_hash, entries = _verified_entries(source, export, trusted_keys, audience, max_age_seconds, now)
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
