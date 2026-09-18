# Transcript Extraction Gem Reference

## Overview

The Transcript Extraction Gem (TE Gem) is the first-stage processor in the TIE source-preservation pipeline.

**Role:** First-pass knowledge extraction from conversational transcripts  
**Output:** SOURCE representation consumed by TIE  
**Specification Status:** COMPLETE (available in GEMS repository)

## Integration with TIE

The TE Gem operates UPSTREAM of TIE's full pipeline:

```
TRANSCRIPT (raw conversation material)
    ↓
TRANSCRIPT EXTRACTION GEM
    ├─ Extract projects, systems, goals, requirements, decisions
    ├─ Preserve EXPLICIT / INFERRED / UNCERTAIN distinctions
    ├─ Preserve epistemic status (FACT, INFERENCE, ASSUMPTION, etc.)
    ├─ Build terminology glossary
    ├─ Trace all extractions back to source
    └─ Produce Transcript Extraction Package
    ↓
SOURCE (structured extraction package)
    ↓
TIE PIPELINE (COVERAGE → EVIDENCE → ARTIFACTS → ... → ROUTING)
    ↓
DURABLE INTELLIGENCE PACKAGE
```

## TE Gem Operating Principles

### Core Operating Rule

For every extracted item, maintain the distinction between:
- **EXPLICIT:** Information directly stated in the transcript
- **INFERRED:** Conclusion reasonably derived from explicit information
- **UNCERTAIN:** Information for which the transcript does not provide enough evidence

Never present an inference as an explicit fact.  
Never convert uncertainty into certainty.  
Never fill missing information with plausible guesses.

### Extraction Objectives

The TE Gem extracts and preserves:

1. **Projects and Systems** — name, purpose, status, relationships, technical details
2. **Goals and Objectives** — explicit goals, business goals, technical goals, success criteria
3. **Requirements** — functional, technical, data, security, governance, compliance, performance
4. **Decisions** — decision, reason given, alternatives discussed, status, evidence
5. **Problems and Failures** — bugs, errors, failed approaches, architectural weaknesses
6. **Solutions and Proposals** — implemented, proposed, workarounds, architectural proposals
7. **Technical Information** — languages, frameworks, libraries, APIs, databases, configurations
8. **Artifacts** — source files, code, repositories, specifications, documents, schemas
9. **Terminology** — project-specific glossary with definitions and aliases
10. **Constraints and Boundaries** — must/must-not, required/prohibited, dependencies, scope
11. **Assumptions** — explicit and inferred assumptions, assumptions later challenged
12. **Open Questions** — unresolved questions, missing information, pending decisions
13. **Contradictions and Changes** — conflicting positions, changed architecture, different versions
14. **Chronology** — timeline of major stages, significant changes, decisions, milestones
15. **People and Organizations** — named entities materially relevant to the project
16. **User Instructions** — formatting requirements, preferences, quality standards, workflows

### Evidence Preservation

Every extracted item must have traceable source information:
- Transcript message number
- Speaker / timestamp
- Section or paragraph reference
- Recognizable source excerpt

Important facts include supporting evidence excerpts.

### Status Classification

Extracted information is classified as:
- **CURRENT** — active, present state
- **PROPOSED** — suggested, not yet decided
- **IMPLEMENTED** — completed, done
- **TESTED** / **VERIFIED** — validated
- **REJECTED** — explicitly not adopted
- **SUPERSEDED** — replaced by later version
- **ABANDONED** — no longer pursued
- **OPEN** / **UNKNOWN** — unresolved

## Handoff to TIE

The TE Gem produces a **Transcript Extraction Package** containing:

1. **Source metadata** — transcript identifier, date range, size, extraction date
2. **Executive summary** — what the transcript contains (facts vs. uncertainty)
3. **Projects and systems** — with status, purpose, relationships
4. **Goals** — with type and status
5. **Requirements** — with category and status
6. **Decisions** — with reason, status, evidence
7. **Problems and failures** — with observed evidence, status
8. **Solutions and proposals** — with status and problem addressed
9. **Technical inventory** — by category (languages, frameworks, repositories, etc.)
10. **Artifact inventory** — with type, purpose, status, location
11. **Terminology glossary** — with definitions and confidence levels
12. **Constraints and boundaries** — with type and evidence
13. **Assumptions** — explicit/inferred, current/superseded, evidence
14. **Open questions** — with impact and current status
15. **Contradictions and evolution** — with positions, evidence, resolution status
16. **Chronology** — timeline of major developments
17. **People and organizations** — named entities
18. **User instructions** — durable working constraints
19. **High-value source evidence** — most important passages for recovery
20. **Extraction gaps** — identified missing information
21. **Downstream handoff** — summary for next Gem in chain

**TIE receives this package as its SOURCE representation.**

## TIE's Role with TE Gem Extractions

TIE ensures that:

1. **Extracted epistemic labels survive** through RECONSTRUCTION and VALIDATION
2. **Inferences remain labeled as inferences** even after multiple pipeline stages
3. **Source references are traceable** from every knowledge view back to original extraction
4. **Uncertain items remain uncertain** unless independently verified
5. **No silent promotion** of INFERRED to FACT without evidence
6. **No silent rewriting** of EXPLICIT items based on interpretation

The TIE pipeline preserves the TE Gem's extraction integrity while adding higher-level organization, reconstruction, and validation.

## Quality Standards

The TE Gem output is evaluated on:

1. **Completeness** — did it recover important information from the transcript?
2. **Accuracy** — are extractions faithful to source material?
3. **Distinction preservation** — are EXPLICIT/INFERRED/UNCERTAIN labels accurate?
4. **Evidence traceability** — can every extraction be located in source?
5. **No fabrication** — does it avoid unsupported interpretation?
6. **Duplication handling** — does it consolidate or preserve meaningful repetition?
7. **Status accuracy** — are project states correctly identified?

## References

- **GEMS Repository** — Contains Transcript Extraction Gem specification and reference implementation
- **TIE ARCHITECTURE.md** — Integration pattern and boundary preservation rules
- **TIE SOURCE.md** — Details on SOURCE representation consumed from TE Gem
