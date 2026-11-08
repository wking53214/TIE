# TIE: Transcript Intelligence Engine

Reconstructed **transcript → evidence-preserving package** baseline. Principle: **PRESERVE BEFORE INTERPRET.** Not the historical TIE; `BUILD_STATUS.md` classifies structure as RECONSTRUCTED.

## 1. Pipeline Position & Role

**SPECIALIZED INLET.** Conceptual Gem-layer 1 / source package for GEMS. Optional `tie_governance_adapter.py` in observe-perceive. Handoff is data, **not execution**.

Second hop of the evidence spine (see "Role in the STACK spine" below): it takes HERALD's signed claim export in as evidence records, and refuses an export that does not verify or that was read from different text.

## 2. Full System Scope & Architectural Depth

Intended stages: SOURCE → COVERAGE → EVIDENCE → ARTIFACTS → IDENTITY → RELATIONSHIPS → RECONSTRUCTION → VALIDATION → KNOWLEDGE VIEWS → TYPED HANDOFF → ROUTING.

**What the functions actually do:**

- `create_source`: wrap a string
- `segment_source(max_chars=4000)`: char windows + sha256; `INSPECTED` unless the caller declares otherwise: `not_inspected=[(start, end)]` marks the segments those ranges touch `NOT_INSPECTED`, and `declared_length=` (when the content is a truncated copy) records the rest as `MISSING`. TIE does not detect gaps itself; it records the ones it is told about
- `evidence_from_statement`: caller supplies the statement (**no NLP**)
- `evidence_from_herald_export` / `signoffs_from_herald_export` (`src/tie/evidence/herald_intake.py`): turn the admitted claims of a HERALD export into `EvidenceRecord`s (machine readings as `INFERRED`, a named person's confirmation on its own `signoff-` path with `HUMAN_ACCEPTED_AI` provenance). Both refuse unless the export is signed by a public key the caller pins in `trusted_keys` (TIE checks the signature itself; a caller cannot supply a verifier), and refuse any claim whose `source_hash` is not the SHA-256 of the source text offered. Evidence ids are derived from source hash, kind, span and text, so replaying the same export gives the same ids. These functions do not check that a claim's raw text occurs at its declared span in the source: a matching source hash identifies the document, not the quoted text or its offsets. These two functions are not re-exported from `tie/__init__.py`; import them from `tie.evidence.herald_intake`
- `reconstruct_summary`: join evidence as `"- {statement}"` bullets
- `build_package` / `validate_package`: source present, coverage id match, evidence refs, reconstruction cites evidence, `routing_not_execution=True` (**hardcoded True**)

90% of substance: frozen dataclasses in `src/tie/models/core.py`. Identity/relationship/handoff/provenance packages mostly re-export.

Enums: `EpistemicStatus{EXPLICIT,INFERRED,UNKNOWN,CONFLICTED}`, `OriginKind{HUMAN,AI,HUMAN_ACCEPTED_AI,UNKNOWN}`, `CoverageStatus`, `BuildClassification`.

## 3. What It Does NOT Do / Non-Goals

Does not extract from transcripts, talk to a model, persist, implement the Transcript Extraction Gem, or recover original TIE. Does not execute. See also the owns / does-not-own lists below.

## 4. Brutally Honest Current Status & Gaps

Commercial: **FEATURE; suite thin for what it claims** (it began as an integration happy path, historically `9 passed in 0.09s`; see the counts below). Schema labeled reconstructed. Knowledge views `{}`. No TE Gem in-repo. GEMS's older `require_tie_adapter()` slot **raises** `TIEIntegrationMissing`, but GEMS has a separate TIE package source adapter (see section 7).

One runtime dependency: `cryptography`, used for the HERALD signature check. The CNS connector is optional. Python ≥ 3.11.

### Release and test status

Originally measured 2026-10-31 at main `f5551d9`. Test and lint counts re-measured 2026-11-06 at main `4fa7d9f`.

| What | State |
|---|---|
| Version | 0.1.0 (`pyproject.toml`) |
| Tag and GitHub Release | None yet. Tagging is the owner's decision. |
| CI workflow | `.github/workflows/tests.yml` runs pytest on Python 3.11, 3.12 and 3.13, with and without CNS. The latest run on main (HEAD `1ab4143`, run 42537187754, 2026-11-08) passed all six jobs. |
| Tests | `python -m pytest tests -q`: 195 passed with CNS importable and `jsonschema` installed (local run, Python 3.13, 2026-11-08, main `f3e1c54`, CNS v2.3.0 installed). Without `cns`, the count was last measured 2026-11-06 at `4fa7d9f` (67 passed, 1 skipped) and has not been re-measured since. |
| Lint | `ruff check .` (ruff 0.16.9, default config, no ruff settings in `pyproject.toml`) reports 69 findings, 43 of them auto-fixable. An earlier revision of this README recorded 32 under a different ruff version; the count depends on the version. CI does not run ruff. |
| CNS pin | The optional `cns` extra is pinned to the tag v2.3.0 (`pyproject.toml`) |

### Running the spine check (from CNS)

The check lives in the CNS repository, not this one. To run it:

1. Check out the CNS repository, and check out HERALD, TIE, Conservation_Kernel, Governance_Gateway and ccc into one shared parent folder, next to CNS.
2. Install the `cryptography` package for Python 3.11 or newer. Installing TIE's optional CNS extra is not needed for this check.
3. Put the CNS folder and each sibling's source folder on the Python path, then run the spine script from the CNS folder.
4. A clean run defines 52 scenarios, 3 of them recorded gaps (the seams nothing checks yet), then prints 4 more checks: 56 results in all, with no failures and exit 0.

Results depend on the sibling repository versions. A run on other commits may differ, and that should be recorded with the run.

## 5. Core Invariants & Guarantees

Validation can fail a package. Empty statement → `ValueError`. `routing_not_execution` cannot fail (always True). Segment checksums exist. No ledger.

## 6. Inputs, Outputs & Type Contracts

`TIEPackage`, `TypedHandoff`, `EvidenceRecord`, `CoverageSegment`, `Provenance`, `SourceRef`. See `schemas/tie_package.reconstructed.schema.json`.

## 7. Stack Integration Topology

```text
(missing TE Gem) → TIE types → GEMS (older slot raises; `TIEPackageSource` adapter exists) / Resume_OS (conceptual)
observe-perceive tie_governance_adapter (opt)
```

The older topology above is the GEMS-side view. The spine view follows in the next section.

### Place in the evidence spine

The evidence spine is the five repositories a document passes through in order: HERALD reads it and extracts claims, TIE records the evidence, Conservation_Kernel decides whether a root may be admitted, Governance_Gateway judges the admission door, and CCC takes the document into its store. CNS holds the roster that makes the decision, the check that every seat judged the same document, and the one-use guard that lets an approved decision open only the door it judged. `chains/evidence_spine.py` in CNS runs all of it end to end. Measured 2026-11-07 with each repository at its default branch (CNS 19c92c5, HERALD 5505d55, TIE 897f033, Conservation_Kernel 3aab1ae, Governance_Gateway 1bede83, ccc 6f80792): exit 0, 52 scenarios plus 4 checks (56 results) all ok, 3 recorded GAPs (including a kernel built without its guard and called directly), which the script asserts as stated facts and never skips. An earlier run on 2026-10-30 reported 30 results and one GAP; that count is superseded.

TIE is the second hop. It records evidence from statements the caller supplies or from a verified HERALD export and writes no records of its own: it persists nothing and has no ledger, so it has no write permission to gate. Its package and handoff can be bound to a CNS verdict (section 8), so a verdict can be checked against the exact package it was about.

**Gate position.** TIE holds no gate position: it judges nothing and creates no CNS `GateResult`. `src/tie/cns_connector.py` only computes a digest of a package or handoff and checks (`binds`) that a verdict from some other gate was judged on exactly that content. The verdict comes from another repository's gate, so TIE is not on the ALPHA or OMEGA end of any chain.

## Role in the STACK spine

**Purpose.** TIE is where a document's extracted claims become preserved evidence. It records each admitted claim with its source identity and available segment reference, with coverage that states which parts of the source were and were not read, and it refuses input whose source hash does not match the text offered. Exact claim-to-source offset verification and retention are not implemented. It does not decide whether any of it is true.

**Responsibilities (implemented in this repo).**
- Hold the data shapes: `SourceRecord`, `Coverage`/`CoverageSegment`, `EvidenceRecord`, `TIEPackage`, `TypedHandoff` (`src/tie/models/core.py`).
- Segment a source with checksums and record declared gaps (`src/tie/coverage/segmenter.py`).
- Take a HERALD export in as evidence, fail closed (`src/tie/evidence/herald_intake.py`).
- Build and validate a package; report coverage gaps as warnings and in the handoff (`src/tie/package/builder.py`, `src/tie/validation/validate.py`).
- Optionally compute a deterministic content digest of a package or handoff so a CNS verdict can be checked against it (`src/tie/cns_connector.py`).

**Inputs and outputs.**

| Direction | What |
|---|---|
| In | A source string (`create_source`), caller-supplied statements, or a HERALD export mapping plus the pinned public keys (`trusted_keys`) that verify it |
| Out | `EvidenceRecord` lists, `TIEPackage`, `TypedHandoff` (frozen dataclasses, JSON schema in `schemas/`), and optionally a plain-data content dict and digest for CNS binding |

**Relationship to companions.** Verified for this revision: TIE's own source. The CNS spine script (`chains/evidence_spine.py`) was checked on 2026-11-07 by reading its source for where it imports TIE and calls into it. On 2026-11-07 the script was run once, from a CNS checkout, and printed 56 results (52 scenarios and 4 checks) with 3 recorded gaps and no failures. That run used each sibling repository's default branch, not the commits the CI workflow pins. The sibling repositories below, except GEMS and observe-perceive, were not checked. Rows marked "not checked" were not verified against the sibling repository's source.

| Repository | Relationship to TIE |
|---|---|
| [HERALD](https://github.com/wking53214/HERALD) | Upstream. TIE imports nothing from HERALD. It takes HERALD's version 3 export (an Ed25519 signature) and verifies it itself against the public keys the caller pins (`trusted_keys`). It does not accept a verifier function from the caller. |
| [Conservation_Kernel](https://github.com/wking53214/Conservation_Kernel) | Downstream in the spine. The CNS spine script's docstring states that no repository ships the step from TIE evidence to a kernel root; the script writes that step itself and builds the kernel with an evidence guard (`tie_evidence_guard`) that accepts only records TIE produced. Kernel source not checked. |
| [Governance_Gateway](https://github.com/wking53214/Governance_Gateway), [CCC](https://github.com/wking53214/CCC), [CCCb](https://github.com/wking53214/CCCb) | Further downstream in the spine per the CNS script. TIE has no code that touches them. Their source was not checked. |
| [CNS](https://github.com/wking53214/CNS) | Shared-contract foundation. Holds shapes, not decisions. See the CNS interaction below. |
| [Link](https://github.com/wking53214/Link) | Not referenced by TIE source. No relationship established (Link's own source not checked). |
| [GEMS](https://github.com/wking53214/GEMS), [observe-perceive](https://github.com/wking53214/observe-perceive) | GEMS: the older `require_tie_adapter()` slot raises, but GEMS has a separate `TIEPackageSource` adapter that turns a TIE package into a GEMS artifact (checked in the GEMS repo, 2026-11-06, with tests there). observe-perceive: optional duck-typed adapter (`tie_governance_adapter.py`); does not import TIE (checked in the hub repo, 2026-11-07). |

```text
HERALD ──signed export──▶ TIE ──evidence records──▶ (caller-written step) ──▶ Conservation_Kernel ─▶ Governance_Gateway ─▶ CCC
 reads + extracts         records, refuses a            CNS spine script only                     (each judges its own door)
 claims                   changed or unverified export

CNS (optional, one-way for TIE): tie.cns_connector ─▶ cns.gate.subject_digest / GateResult.binds
CNS spine script (chains/evidence_spine.py) ─▶ imports tie.evidence.herald_intake
```

**Owns.** The shapes and invariants of a transcript evidence package; the rule that evidence from HERALD enters only through a verified export whose claims match the source text hash; the rule that a person's sign-off enters on its own path and is never taken for a machine reading; the digest of a TIE package or handoff.

**Does not own.** Whether a claim is true (HERALD judges the document and each claim; TIE records). Permission or admission of anything (Conservation_Kernel, Governance_Gateway and CCC judge their own doors; the receiver's own policy permits). HERALD's signature or key (the caller supplies the verifier). Persistence or a ledger (TIE writes nothing). Transcript extraction (no NLP, no model). Any CNS verdict: TIE can be named in one but never issues one.

**CNS interaction: PARTIAL.**
- Implemented, TIE side: an optional connector that makes a package or handoff nameable for a CNS verdict and checks a `cns.gate.GateResult` against it: `src/tie/cns_connector.py` (lazy `importlib` of `cns.gate`, the `subject_digest` function, and the `binds` function). Tested in `tests/test_cns_connector.py` and `tests/test_cns_independence.py` (CNS blocked).
- Implemented, CNS side: CNS's spine script imports TIE's intake (`herald_intake` in `chains/evidence_spine.py` in the CNS repo, and calls into it at several points; checked 2026-11-07 by reading the source, and run once that day, see the next section). That is CNS using TIE, not TIE using CNS.
- Absent: no TIE code imports `cns`, `cns_interop` or `cns_composition` at module load, and nothing in `src/tie` calls the connector. TIE issues no verdict, defines no gate, and has no UAI-1 signed-message code (checked by grep over `src`; the only `cns` references are in `cns_connector.py`).
- So the integration is binding only. A CNS verdict about a TIE package is possible to check, but nothing in TIE produces or requires one.

**Maturity and limitations (measured 2026-10-31, main `f5551d9`).**
- 195 tests pass with CNS importable (measured 2026-11-08, main `f3e1c54`). Without CNS: 67 pass and 1 skips (measured 2026-11-06, main `4fa7d9f`; not re-measured since). One runtime dependency (`cryptography`).
- The package model is a reconstruction (`BUILD_STATUS.md`), not the historical TIE.
- Intake records `INFERRED` evidence only; it never produces `EXPLICIT`.
- The `routing_not_execution` check in `validate_package` is hardcoded `True` (in `src/tie/validation/validate.py`) and cannot fail.
- Intake refuses unless the export is a version 3 HERALD export signed by a key in `trusted_keys`. The caller pins the keys; TIE checks the signature itself. A version 2 export (in-process HMAC) is refused, because only the producing process could check it.
- No persistence, no ledger, no key handling, no transport.

## 8. Optional CNS Connection

TIE does not need CNS. Its only runtime dependency is `cryptography`, and nothing in the package imports CNS when it loads, and `tests/test_cns_independence.py` checks this with CNS blocked. `src/tie/cns_connector.py` is the one place that knows CNS exists. Install it with `pip install 'tie-transcript-intelligence-engine[cns]'`; without CNS, asking for a digest raises `CnsNotInstalled` and nothing else changes.

**What is bound.** A `TIEPackage` (`package_content`, `package_digest`) or a `TypedHandoff` (`handoff_content`, `handoff_digest`), as plain deterministic data: the package id, the source (id, media type, title, provenance, and a SHA-256 and length of the transcript instead of the transcript), every coverage segment with its status and checksum, all evidence, artifacts, identity references and relationships, the reconstruction, the validation result, the knowledge views, the handoff, the routing signal and the build classification. `binds(result, obj)` says whether a `cns.gate.GateResult` was issued against exactly that output, using the subject labels `tie.package` and `tie.handoff`. A verdict about one package does not bind to another, nor to a package whose coverage says a different part of the source was read.

**Binding only, and why.** There is no gate, verdict mapping or chain here. TIE preserves before it interprets and does not judge, and its handoff stays data, not execution. Whether a package is good enough for anything is for the repository that issues the verdict. This only lets that verdict be checked against the package it was about.

Apache-2.0. Read `BUILD_STATUS.md` before relying on the ambition described in the other docs.
