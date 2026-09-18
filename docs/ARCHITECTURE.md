# TIE Architecture — Reconstructed Implementation Baseline

## Current architecture

The five recovery summaries converge on an upstream transcript-intelligence boundary with these durable information areas:

`SOURCE → COVERAGE → EVIDENCE → ARTIFACTS / IDENTITY_REFERENCES / RELATIONSHIPS`

Derived layers are:

`RECONSTRUCTION → VALIDATION → KNOWLEDGE_VIEWS / TYPED_HANDOFF / ROUTING_SIGNAL`

A second recovered formulation — segmentation, local extraction, and global reconciliation — is treated here as the internal processing decomposition, not as a competing source-of-truth architecture.

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
- Maintain traceability from every downstream item back to source extraction
- Prevent reconstruction or validation from silently replacing original evidence

**Input:** TE Gem output | **Output:** Durable intelligence package with full provenance chain.

### Boundary preservation rules

1. TE Gem operates on **conversational source material** (transcripts)
2. TIE operates on **extracted information** (SOURCE onwards)
3. TIE does **not** re-extract from transcripts; it preserves TE Gem extractions
4. Epistemic labels from TE Gem extraction are carried through TIE pipeline unchanged
5. Source references from TE Gem remain traceable through reconstruction and validation

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

**UPDATE:** The Transcript Extraction Gem ↔ TIE boundary has been formally defined (this section). Historical unresolved status is now RESOLVED_BY_SPECIFICATION.
