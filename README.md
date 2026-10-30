# TIE — Transcript Intelligence Engine

Reconstructed **transcript → evidence-preserving package** baseline. Principle: **PRESERVE BEFORE INTERPRET.** Not the historical TIE; `BUILD_STATUS.md` classifies structure as RECONSTRUCTED.

## 1. Pipeline Position & Role

**SPECIALIZED INLET.** Conceptual Gem-layer 1 / source package for GEMS. Optional `tie_governance_adapter.py` in observe-perceive. Handoff is data, **not execution**.

## 2. Full System Scope & Architectural Depth

Intended stages: SOURCE → COVERAGE → EVIDENCE → ARTIFACTS → IDENTITY → RELATIONSHIPS → RECONSTRUCTION → VALIDATION → KNOWLEDGE VIEWS → TYPED HANDOFF → ROUTING.

**What the functions actually do:**

- `create_source` — wrap a string
- `segment_source(max_chars=4000)` — char windows + sha256; `INSPECTED` unless the caller declares otherwise: `not_inspected=[(start, end)]` marks the segments those ranges touch `NOT_INSPECTED`, and `declared_length=` (when the content is a truncated copy) records the rest as `MISSING`. TIE does not detect gaps itself; it records the ones it is told about
- `evidence_from_statement` — caller supplies the statement (**no NLP**)
- `reconstruct_summary` — join evidence as `"- {statement}"` bullets
- `build_package` / `validate_package` — source present, coverage id match, evidence refs, reconstruction cites evidence, `routing_not_execution=True` (**hardcoded True**)

90% of substance: frozen dataclasses in `src/tie/models/core.py`. Identity/relationship/handoff/provenance packages mostly re-export.

Enums: `EpistemicStatus{EXPLICIT,INFERRED,UNKNOWN,CONFLICTED}`, `OriginKind{HUMAN,AI,HUMAN_ACCEPTED_AI,UNKNOWN}`, `CoverageStatus`, `BuildClassification`.

## 3. What It Does NOT Do / Non-Goals

Does not extract from transcripts, talk to a model, persist, implement the Transcript Extraction Gem, or recover original TIE. Does not execute.

## 4. Brutally Honest Current Status & Gaps

Commercial: **FEATURE; suite thin for what it claims** (it began as an integration happy path, historically `9 passed in 0.09s`; see the counts below). Schema labeled reconstructed. Knowledge views `{}`. No TE Gem in-repo. GEMS `require_tie_adapter()` **raises** `TIEIntegrationMissing`.

Zero runtime deps. Python ≥ 3.11.

### Release and test status

Measured 2026-10-30 at main `09d9b2a`.

| What | State |
|---|---|
| Version | 0.1.0 (`pyproject.toml`) |
| Tag and GitHub Release | None yet. Tagging is the owner's decision. |
| CI on main | Green (tests on Python 3.11, 3.12 and 3.13, with and without CNS) |
| Tests | 61 passed and 1 skipped without CNS, 182 passed with the `cns` extra installed |
| Lint | `ruff check .` reports 32 findings (mostly star imports in `src/tie/__init__.py`). CI does not run ruff, so none of them is red anywhere. |
| CNS pin | The optional `cns` extra is pinned to the tag v2.2.0, the same as the rest of the spine |

## 5. Core Invariants & Guarantees

Validation can fail a package. Empty statement → `ValueError`. `routing_not_execution` cannot fail (always True). Segment checksums exist. No ledger.

## 6. Inputs, Outputs & Type Contracts

`TIEPackage`, `TypedHandoff`, `EvidenceRecord`, `CoverageSegment`, `Provenance`, `SourceRef`. See `schemas/tie_package.reconstructed.schema.json`.

## 7. Stack Integration Topology

```text
(missing TE Gem) → TIE types → GEMS (unwired, raises) / Resume_OS (conceptual)
observe-perceive tie_governance_adapter (opt)
```

### Place in the evidence spine

The evidence spine is the five repositories a document passes through in order: HERALD reads it and extracts claims, TIE records the evidence, Conservation_Kernel decides whether a root may be admitted, Governance_Gateway judges the admission door, and CCC takes the document into its store. CNS holds the roster that makes the decision, the check that every seat judged the same document, and the one-use guard that lets an approved decision open only the door it judged. `chains/evidence_spine.py` in CNS runs all of it end to end. Measured 2026-10-30 with every repository at main: 30 results, all ok, and exactly one recorded GAP (a kernel built without its guard and called directly), which the script asserts as a stated fact and never skips.

TIE is the second hop. It records evidence from statements the caller supplies and writes no records of its own: it persists nothing and has no ledger, so it has no write permission to gate. Its package and handoff can be bound to a CNS verdict (section 8), so a verdict can be checked against the exact package it was about.

## 8. Optional CNS Connection

TIE does not need CNS. It has no runtime dependency, nothing in the package imports CNS when it loads, and `tests/test_cns_independence.py` checks this with CNS blocked. `src/tie/cns_connector.py` is the one place that knows CNS exists. Install it with `pip install 'tie-transcript-intelligence-engine[cns]'`; without CNS, asking for a digest raises `CnsNotInstalled` and nothing else changes.

**What is bound.** A `TIEPackage` (`package_content`, `package_digest`) or a `TypedHandoff` (`handoff_content`, `handoff_digest`), as plain deterministic data: the package id, the source (id, media type, title, provenance, and a SHA-256 and length of the transcript instead of the transcript), every coverage segment with its status and checksum, all evidence, artifacts, identity references and relationships, the reconstruction, the validation result, the knowledge views, the handoff, the routing signal and the build classification. `binds(result, obj)` says whether a `cns.gate.GateResult` was issued against exactly that output, using the subject labels `tie.package` and `tie.handoff`. A verdict about one package does not bind to another, nor to a package whose coverage says a different part of the source was read.

**Binding only, and why.** There is no gate, verdict mapping or chain here. TIE preserves before it interprets and does not judge, and its handoff stays data, not execution. Whether a package is good enough for anything is for the repository that issues the verdict. This only lets that verdict be checked against the package it was about.

Apache-2.0. Read `BUILD_STATUS.md` before `README` ambition pages.
