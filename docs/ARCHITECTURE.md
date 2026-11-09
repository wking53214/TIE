# TIE Architecture: Reconstructed Implementation Baseline

## Current architecture

The five recovery summaries converge on an upstream transcript-intelligence boundary with these durable information areas:

`SOURCE → COVERAGE → EVIDENCE → ARTIFACTS / IDENTITY_REFERENCES / RELATIONSHIPS`

Derived layers are:

`RECONSTRUCTION → VALIDATION → KNOWLEDGE_VIEWS / TYPED_HANDOFF / ROUTING_SIGNAL`

A second recovered formulation (segmentation, local extraction, and global reconciliation) is treated here as the internal processing decomposition, not as a competing source-of-truth architecture.

## Historical/superseded architecture

An earlier individual-chat → TIE → digestible-chunks → Gem Chain design is retained as historical lineage and is not implemented as the current architecture.

## Transcript Extraction Gem boundary

The Transcript Extraction Gem (TE Gem) provides first-pass knowledge extraction from conversational transcripts. It produces the **SOURCE** representation that TIE consumes.

### TE Gem responsibility (upstream)

- Extract materially useful information from transcripts
- Preserve distinction: EXPLICIT / INFERRED / UNCERTAIN
- Maintain epistemic status (FACT / INFERENCE / ASSUMPTION / RECOMMENDATION / DECISION / UNKNOWN)
- Build terminology glossary
- Identify projects, goals, requirements, decisions, problems, solutions
- Extract technical details, artifacts, constraints, assumptions, open questions
- Produce Transcript Extraction Package with evidence-traced source references

**Output:** Structured extraction package that becomes TIE SOURCE.

### TIE responsibility (downstream)

- Receive SOURCE representation from TE Gem
- Apply full preservation pipeline: COVERAGE → EVIDENCE → ARTIFACTS → IDENTITY/REFERENCES → RELATIONSHIPS → RECONSTRUCTION → VALIDATION → KNOWLEDGE_VIEWS → TYPED_HANDOFF → ROUTING
- Intended requirement: traceability from every downstream item back to source extraction. Not enforced as a general guarantee
- Intended requirement: reconstruction must not replace original evidence. The only current check is that a reconstruction cites evidence IDs (`src/tie/validation/validate.py`); nothing else enforces this

**Input:** TE Gem output | **Output:** Durable intelligence package with content hashes and references. End-to-end provenance is not independently verified.

### Boundary preservation rules

1. TE Gem operates on **conversational source material** (transcripts)
2. TIE operates on **extracted information** (SOURCE onwards)
3. TIE does **not** re-extract from transcripts; it preserves TE Gem extractions
4. Intended requirement: epistemic labels from TE Gem extraction should be carried through the TIE pipeline unchanged. Not enforced today. TIE's own labels are EXPLICIT, INFERRED, UNKNOWN and CONFLICTED (`docs/EPISTEMIC_MODEL.md`), and the TE Gem vocabulary above differs from them. No mapping between the two is implemented
5. Intended requirement: source references from TE Gem should remain traceable through reconstruction and validation. Only evidence-ID citation is checked today

### Integration pattern

```
TRANSCRIPT
    ↓
TRANSCRIPT EXTRACTION GEM
  (first-pass, evidence-preserving extraction)
    ↓
SOURCE (extraction package)
    ↓
TIE PIPELINE
  (preservation, evidence traceability, reconstruction, validation)
    ↓
DURABLE INTELLIGENCE PACKAGE
```

## Reconciliation status

This exact combined sequence is a forensic synthesis. It is not claimed to be an original historical diagram.

**UPDATE:** The Transcript Extraction Gem ↔ TIE boundary is specified in this section. The TE Gem itself is not implemented in this repository (see `README.md`), so the boundary is a specification, not a tested integration.
