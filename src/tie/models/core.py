from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any, Mapping
import json


class EpistemicStatus(str, Enum):
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


class OriginKind(str, Enum):
    HUMAN = "HUMAN"
    AI = "AI"
    HUMAN_ACCEPTED_AI = "HUMAN_ACCEPTED_AI"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class CoverageStatus(str, Enum):
    INSPECTED = "INSPECTED"
    NOT_INSPECTED = "NOT_INSPECTED"
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"


class BuildClassification(str, Enum):
    RECOVERED = "RECOVERED"
    PARTIALLY_RECOVERED = "PARTIALLY_RECOVERED"
    RECONSTRUCTED = "RECONSTRUCTED"
    IMPLEMENTED_FROM_RECOVERED_SPEC = "IMPLEMENTED_FROM_RECOVERED_SPEC"
    PROPOSED = "PROPOSED"
    SUPERSEDED = "SUPERSEDED"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


def to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_primitive(v) for k, v in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(k): to_primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_primitive(v) for v in value]
    return value


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_location: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    segment_id: str | None = None


@dataclass(frozen=True)
class Provenance:
    source: SourceRef | None = None
    origin: OriginKind = OriginKind.UNKNOWN
    extraction_origin: str | None = None
    transformation_origin: str | None = None
    lineage_id: str | None = None
    version: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    content: str
    media_type: str = "text/plain"
    title: str | None = None
    provenance: Provenance = field(default_factory=Provenance)


@dataclass(frozen=True)
class CoverageSegment:
    segment_id: str
    ordinal: int
    start_char: int
    end_char: int
    status: CoverageStatus = CoverageStatus.INSPECTED
    source_id: str | None = None
    checksum: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Coverage:
    source_id: str
    segments: tuple[CoverageSegment, ...] = ()

    @property
    def inspected_segments(self) -> tuple[CoverageSegment, ...]:
        return tuple(s for s in self.segments if s.status is CoverageStatus.INSPECTED)

    @property
    def complete(self) -> bool:
        return bool(self.segments) and all(
            s.status is CoverageStatus.INSPECTED for s in self.segments
        )


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    statement: str
    epistemic_status: EpistemicStatus
    source_ref: SourceRef
    provenance: Provenance
    segment_id: str | None = None
    artifact_ids: tuple[str, ...] = ()
    relationship_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    name: str
    artifact_type: str | None = None
    source_refs: tuple[SourceRef, ...] = ()
    provenance: Provenance = field(default_factory=Provenance)
    version: str | None = None
    supersedes: tuple[str, ...] = ()
    identity_uncertain: bool = False
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityReference:
    reference_id: str
    identity_key: str
    source_ref: SourceRef
    confidence_note: str | None = None
    uncertain: bool = False


@dataclass(frozen=True)
class Relationship:
    relationship_id: str
    subject_id: str
    predicate: str
    object_id: str
    epistemic_status: EpistemicStatus = EpistemicStatus.EXPLICIT
    provenance: Provenance = field(default_factory=Provenance)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Reconstruction:
    reconstruction_id: str
    text: str
    evidence_ids: tuple[str, ...]
    epistemic_status: EpistemicStatus
    provenance: Provenance
    conflict_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    checks: Mapping[str, bool]
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TypedHandoff:
    objective: str
    source_id: str
    evidence_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    known_uncertainty: tuple[str, ...]
    routing_signal: str | None = None
    provenance: Provenance = field(default_factory=Provenance)


@dataclass(frozen=True)
class TIEPackage:
    package_id: str
    source: SourceRecord
    coverage: Coverage
    evidence: tuple[EvidenceRecord, ...]
    artifacts: tuple[Artifact, ...] = ()
    identity_references: tuple[IdentityReference, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    reconstruction: Reconstruction | None = None
    validation: ValidationResult | None = None
    knowledge_views: Mapping[str, Any] = field(default_factory=dict)
    typed_handoff: TypedHandoff | None = None
    routing_signal: str | None = None
    build_classification: BuildClassification = BuildClassification.RECONSTRUCTED

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
