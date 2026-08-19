"""Transcript Intelligence Engine (TIE) reconstructed implementation baseline."""

from .models import *
from .source import create_source
from .coverage import segment_source
from .evidence import evidence_from_statement
from .reconstruction import reconstruct_summary
from .package import build_package
from .validation import validate_package

__all__ = [
    "SourceRecord", "Coverage", "CoverageSegment", "EvidenceRecord", "Artifact",
    "IdentityReference", "Relationship", "Reconstruction", "ValidationResult",
    "TypedHandoff", "TIEPackage", "EpistemicStatus", "OriginKind", "CoverageStatus",
    "BuildClassification", "Provenance", "SourceRef", "create_source", "segment_source",
    "evidence_from_statement", "reconstruct_summary", "build_package", "validate_package",
]
