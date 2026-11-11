# Build Status

## Corpus

Five user-supplied TIE forensic summaries reconciled as one corpus.

## Current implementation classification

- Repository structure: RECONSTRUCTED
- Runtime models: NEW IMPLEMENTATION FROM RECOVERED SPECIFICATION
- Tests: RECONSTRUCTED TESTS FROM RECOVERED INVARIANTS
- JSON schema: RECONSTRUCTED / IMPLEMENTATION BASELINE
- Historical source code: NOT RECOVERED
- Historical exact package contract: NOT RECOVERED
- Historical exact test results: NOT RECOVERED

## Actual execution

Measured 2026-11-08 at main `f3e1c54`:

- With the CNS package installed (pinned to v3.0.0) and `jsonschema` installed: `195 passed`.
- Without CNS: `67 passed, 1 skipped` (the CNS connector tests skip), last measured 2026-11-06 at main `4fa7d9f`; not re-measured since.

These are measurements of this reconstructed implementation. They are not historical TIE test results. An earlier run recorded 9 tests.
