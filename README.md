# TIE — Transcript Intelligence Engine

Reconstructed **transcript → evidence-preserving package** baseline. Principle: **PRESERVE BEFORE INTERPRET.** Not the historical TIE; `BUILD_STATUS.md` classifies structure as RECONSTRUCTED.

## 1. Pipeline Position & Role

**SPECIALIZED INLET.** Conceptual Gem-layer 1 / source package for GEMS. Optional `tie_governance_adapter.py` in observe-perceive. Handoff is data, **not execution**.

## 2. Full System Scope & Architectural Depth

Intended stages: SOURCE → COVERAGE → EVIDENCE → ARTIFACTS → IDENTITY → RELATIONSHIPS → RECONSTRUCTION → VALIDATION → KNOWLEDGE VIEWS → TYPED HANDOFF → ROUTING.

**What the functions actually do:**

- `create_source` — wrap a string
- `segment_source(max_chars=4000)` — char windows + sha256; **always** `INSPECTED`
- `evidence_from_statement` — caller supplies the statement (**no NLP**)
- `reconstruct_summary` — join evidence as `"- {statement}"` bullets
- `build_package` / `validate_package` — source present, coverage id match, evidence refs, reconstruction cites evidence, `routing_not_execution=True` (**hardcoded True**)

90% of substance: frozen dataclasses in `src/tie/models/core.py`. Identity/relationship/handoff/provenance packages mostly re-export.

Enums: `EpistemicStatus{EXPLICIT,INFERRED,UNKNOWN,CONFLICTED}`, `OriginKind{HUMAN,AI,UNKNOWN}`, `CoverageStatus`, `BuildClassification`.

## 3. What It Does NOT Do / Non-Goals

Does not extract from transcripts, talk to a model, persist, implement the Transcript Extraction Gem, or recover original TIE. Does not execute.

## 4. Brutally Honest Current Status & Gaps

Commercial: **FEATURE; suite too thin** (integration happy path; BUILD_STATUS historically `9 passed in 0.09s`). Schema labeled reconstructed. Knowledge views `{}`. No TE Gem in-repo. GEMS `require_tie_adapter()` **raises** `TIEIntegrationMissing`.

Zero runtime deps. Python ≥ 3.11.

## 5. Core Invariants & Guarantees

Validation can fail a package. Empty statement → `ValueError`. `routing_not_execution` cannot fail (always True). Segment checksums exist. No ledger.

## 6. Inputs, Outputs & Type Contracts

`TIEPackage`, `TypedHandoff`, `EvidenceRecord`, `CoverageSegment`, `Provenance`, `SourceRef`. See `schemas/tie_package.reconstructed.schema.json`.

## 7. Stack Integration Topology

```text
(missing TE Gem) → TIE types → GEMS (unwired, raises) / Resume_OS (conceptual)
observe-perceive tie_governance_adapter (opt)
```

Apache-2.0. Read `BUILD_STATUS.md` before `README` ambition pages.
