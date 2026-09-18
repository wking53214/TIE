# Conflict Ledger

## Pipeline forms

1. SOURCE → SEGMENTS → LOCAL EVIDENCE EXTRACTION → GLOBAL RECONCILIATION
2. SOURCE → COVERAGE → EVIDENCE → ARTIFACTS / IDENTITY / RELATIONSHIPS → RECONSTRUCTION → VALIDATION → TYPED HANDOFF
3. SOURCE → PRESERVE → EXTRACT → CLASSIFY → RELATE → VALIDATE CONSERVATION → TIE_PACKAGE

Status: reconciled as different architectural layers where compatible; exact historical canonical diagram remains unresolved.

## Transcript Extraction Gem boundary

**Status: RESOLVED**

The Transcript Extraction Gem provides first-pass extraction from conversational transcripts. The boundary is now formally defined in `docs/ARCHITECTURE.md`:

- **TE Gem upstream responsibility:** Extract from transcripts, preserve EXPLICIT/INFERRED/UNCERTAIN distinctions, build terminology, produce SOURCE representation
- **TIE downstream responsibility:** Consume SOURCE, apply full preservation pipeline from COVERAGE through ROUTING
- **Boundary rule:** TIE does not re-extract from transcripts; it preserves and traces TE Gem extractions through reconstruction and validation

See `docs/ARCHITECTURE.md` section "Transcript Extraction Gem boundary" for integration pattern and preservation rules.

## Epistemic vocabulary evolution

An earlier recovered instruction set used Confirmed / Assumed / Inferred / Proposed / Unknown. The later architecture converges on Explicit / Inferred / Unknown / Conflicted. The exact historical transition is unresolved.
