# TIE — Transcript Intelligence Engine

## Build classification

This repository is a **reconstructed implementation baseline**, not the recovered original TIE repository.

The five supplied forensic summaries establish a consistent architecture centered on:

- SOURCE
- COVERAGE
- EVIDENCE
- ARTIFACTS
- IDENTITY_REFERENCES
- RELATIONSHIPS

with derived layers for reconstruction, validation, knowledge views, typed handoff, and routing.

The implementation intentionally keeps those boundaries explicit.

## Preservation principle

**PRESERVE BEFORE INTERPRET.**

The source remains independently represented. Evidence points toward source. Reconstruction points toward evidence. Validation is separate from historical truth. Routing is data, not execution authority.

## Recovery status

Original complete TIE repository: not recovered from the supplied material.
Exact historical TIE_PACKAGE schema: not recovered.
Exact historical EvidenceRecord schema: not recovered.
This repository therefore uses the smallest defensible reconstructed contract and labels it as such.

## Python

Python 3.11+; runtime dependencies are intentionally minimal.

## Layout

`src/tie/` contains the reconstructed runtime baseline.
`tests/` contains newly written tests derived from the recovered invariants.
`docs/` and `recovery/` preserve forensic/build provenance.
