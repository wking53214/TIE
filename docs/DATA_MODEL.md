# TIE Data Model

## Container

- `TIEPackage`: holds everything below. Its `knowledge_views` and `routing_signal` are fields on this object, not separate classes.

## Canonical

- `SourceRecord`
- `Coverage` (with `CoverageSegment` entries)
- `EvidenceRecord`
- `Artifact`
- `IdentityReference`
- `Relationship`
- `Provenance` and `SourceRef` (attached to records to say where they came from)

## Derived

- `Reconstruction`
- `ValidationResult`
- `TypedHandoff`
- `knowledge_views` (a field on `TIEPackage`)
- `routing_signal` (a field on `TIEPackage` and `TypedHandoff`)

## Epistemic states

- `EXPLICIT`
- `INFERRED`
- `UNKNOWN`
- `CONFLICTED`

The implementation does not add canonical first-class structures for events, state, decisions, requirements, constraints, assumptions, claims, questions, risks, conflicts, timelines, or workflow state.
