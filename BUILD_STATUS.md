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

Measured 2026-11-16 at commit `db1cc5b` (branch `claude/intake-identity-and-build-pin`), Python 3.13.18, `python -m pytest -q -rs`:

- CNS 4.1.0 importable, `jsonschema` not installed: 381 passed, 1 skipped (the schema conformance tests).
- `jsonschema` installed, no CNS: 266 passed, 1 skipped (the CNS connector tests).
- Neither installed: 260 passed, 2 skipped.
- The CI matrix (3.11, 3.12, 3.13, with and without CNS) runs the same suites; each commit's result is on its Actions page. No single local environment here has both CNS and `jsonschema`, so no one local run executes every test.
- The `cns` extra in `pyproject.toml` pins CNS v4.1.0, the version the local runs above used.

Static checks at the same commit (pinned ruff 0.16.9 and mypy 2.3.1): ruff 79 findings and mypy 7 findings, all recorded in `tools/lint_baseline.json`. CI fails on any finding above that baseline; it does not fix or hide the existing ones.

These are measurements of this reconstructed implementation. They are not historical TIE test results. An earlier run recorded 9 tests. The historical TIE source code remains NOT RECOVERED.
