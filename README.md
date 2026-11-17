# TIE: Transcript Intelligence Engine

Reconstructed **transcript → evidence-preserving package** baseline. Principle: **PRESERVE BEFORE INTERPRET.** Not the historical TIE; `BUILD_STATUS.md` classifies structure as RECONSTRUCTED.

## 1. Pipeline Position & Role

**Where this fits.** TIE is part of ≡TACK, the whole library. It is the second of five repositories in the evidence spine, the path a document takes: HERALD, TIE, Conservation_Kernel, Governance_Gateway, CCC. In this README, "spine" always means that five-repository path, never the whole system. TIE turns HERALD's checked claims into preserved evidence and hands it on. It does not decide what is true.

**SPECIALIZED INLET.** Conceptual Gem-layer 1 / source package for GEMS. Optional `tie_governance_adapter.py` in observe-perceive. Handoff is data, **not execution**.

Second hop of the evidence spine (see "Role in the evidence spine" below): it takes HERALD's signed claim export in as evidence records, and refuses an export that does not verify or that was read from different text.

## 2. Full System Scope & Architectural Depth

Intended stages: SOURCE → COVERAGE → EVIDENCE → ARTIFACTS → IDENTITY → RELATIONSHIPS → RECONSTRUCTION → VALIDATION → KNOWLEDGE VIEWS → TYPED HANDOFF → ROUTING.

**What the functions actually do:**

- `create_source`: wrap a string
- `segment_source(max_chars=4000)`: char windows + sha256; `INSPECTED` unless the caller declares otherwise: `not_inspected=[(start, end)]` marks the segments those ranges touch `NOT_INSPECTED`, and `declared_length=` (when the content is a truncated copy) records the rest as `MISSING`. TIE does not detect gaps itself; it records the ones it is told about
- `evidence_from_statement`: caller supplies the statement (**no NLP**)
- `evidence_from_herald_export` / `signoffs_from_herald_export` (`src/tie/evidence/herald_intake.py`): turn the admitted claims of a HERALD export into `EvidenceRecord`s (machine readings as `INFERRED`, a named person's confirmation on its own `signoff-` path with `HUMAN_ACCEPTED_AI` provenance). Both refuse unless the export is signed by a public key the caller pins in `trusted_keys` (TIE checks the signature itself; a caller cannot supply a verifier), and refuse any claim whose `source_hash` is not the SHA-256 of the source text offered. Evidence ids are derived from source hash, kind, span and text, so replaying the same export gives the same ids. They also refuse any claim whose quoted text is not exactly what the source holds at the claim's declared span (character offsets, start inclusive, end exclusive, no normalization), and they refuse a malformed export or badly typed settings with an `HeraldIntakeRefused` rather than a Python error. These two functions are not re-exported from `tie/__init__.py`; import them from `tie.evidence.herald_intake`. A consumer that checks which source text TIE verified a record against calls `source_sha256_of(record)` from the same module (it reads the `source_sha256: <hex>` note, which is kept as is, in one place; it returns None for a record intake did not make)
- `reconstruct_summary`: join evidence as `"- {statement}"` bullets
- `build_package` / `validate_package`: source present, coverage id match, evidence refs, reconstruction cites evidence, `routing_not_execution` (a real check: the routing signal must be a plain label or absent, and the package and its typed handoff must agree; it is data-shape validation, not an authorization)

90% of substance: frozen dataclasses in `src/tie/models/core.py`. Identity/relationship/handoff/provenance packages mostly re-export.

Enums: `EpistemicStatus{EXPLICIT,INFERRED,UNKNOWN,CONFLICTED}`, `OriginKind{HUMAN,AI,HUMAN_ACCEPTED_AI,UNKNOWN}`, `CoverageStatus`, `BuildClassification`.

## 3. What It Does NOT Do / Non-Goals

Does not extract from transcripts, talk to a model, persist, implement the Transcript Extraction Gem, or recover original TIE. Does not execute. See also the owns / does-not-own lists below.

## 4. Brutally Honest Current Status & Gaps

Commercial: **FEATURE; suite thin for what it claims** (it began as an integration happy path, historically `9 passed in 0.09s`; see the counts below). Schema labeled reconstructed. Knowledge views `{}`. No TE Gem in-repo. GEMS's older `require_tie_adapter()` slot **raises** `TIEIntegrationMissing`, but GEMS has a separate TIE package source adapter (see section 7).

One runtime dependency: `cryptography`, used for the HERALD signature check. The CNS connector is optional. Python ≥ 3.11.

### Release and test status

Numbers below were measured on the date and commit shown in the table.

| What | State |
|---|---|
| Version | 0.1.0 (`pyproject.toml`) |
| Tag and GitHub Release | None yet. Tagging is the owner's decision. |
| CI workflow | `.github/workflows/tests.yml` runs pytest on Python 3.11, 3.12 and 3.13, with and without CNS. This README does not name a commit as current. Each commit's CI result is on its Actions page. |
| Tests | `python -m pytest tests -q -rs`, local runs on Python 3.13.18 at `e7ad5b2`, 2026-11-16: 344 passed and 1 skipped with CNS 4.1.0 importable and no `jsonschema`; 229 passed and 1 skipped with `jsonschema` and no CNS; 223 passed and 2 skipped with neither. No one local environment has both, so see `BUILD_STATUS.md`. The CI matrix runs the suites on 3.11, 3.12 and 3.13, with and without CNS. |
| Lint | `ruff check .` (ruff 0.16.9, default config, no ruff settings in `pyproject.toml`) reports 70 findings, 44 of them auto-fixable (measured 2026-11-10, main `5a0dc59`). An earlier revision of this README recorded 32 under a different ruff version; the count depends on the version. CI does not run ruff. |
| CNS pin | The optional `cns` extra is pinned to the tag v4.0.0 (`pyproject.toml`) |

### Running the spine check (from CNS)

The check lives in the CNS repository, not this one. To run it:

1. Check out the CNS repository, and check out HERALD, TIE, Conservation_Kernel, Governance_Gateway and ccc into one shared parent folder, next to CNS.
2. Install the `cryptography` package for Python 3.11 or newer. Installing TIE's optional CNS extra is not needed for this check.
3. Put the CNS folder and each sibling's source folder on the Python path, then run the spine script from the CNS folder.
4. A clean run defines 52 scenarios, 3 of them recorded gaps (the seams nothing checks yet), then prints 4 more checks: 56 results in all, with no failures and exit 0.

Results depend on the sibling repository versions. A run on other commits may differ, and that should be recorded with the run.

## 5. Core Invariants & Guarantees

Validation can fail a package. Empty statement → `ValueError`. `routing_not_execution` fails for a routing signal that is not a plain label or for a package and handoff that disagree about it. Segment checksums exist. No durable ledger (see the HERALD intake section for the replay ledger).

## 6. Inputs, Outputs & Type Contracts

`TIEPackage`, `TypedHandoff`, `EvidenceRecord`, `CoverageSegment`, `Provenance`, `SourceRef`. See `schemas/tie_package.reconstructed.schema.json`.

## 7. Stack Integration Topology

```text
(missing TE Gem) → TIE types → GEMS (older slot raises; `TIEPackageSource` adapter exists) / Resume_OS (conceptual)
observe-perceive tie_governance_adapter (opt)
```

The diagram above is the GEMS-side view. The spine view follows in the next section.

### Place in the evidence spine

The evidence spine is the five repositories a document passes through in order: HERALD reads it and extracts claims, TIE records the evidence, Conservation_Kernel decides whether a root may be admitted, Governance_Gateway judges the admission door, and CCC takes the document into its store. CNS holds the roster that makes the decision, the check that every seat judged the same document, and the one-use guard that lets an approved decision open only the door it judged. `chains/evidence_spine.py` in CNS runs all of it end to end. Measured 2026-11-07 with each repository at its default branch (CNS 19c92c5, HERALD 5505d55, TIE 897f033, Conservation_Kernel 3aab1ae, Governance_Gateway 1bede83, ccc 6f80792): exit 0, 52 scenarios plus 4 checks (56 results) all ok, 3 recorded GAPs (including a kernel built without its guard and called directly), which the script asserts as stated facts and never skips. An earlier run on 2026-10-30 reported 30 results and one GAP; that count is superseded.

TIE is the second hop. It records evidence from statements the caller supplies or from a verified HERALD export and writes no records of its own: it persists nothing and ships only an in-memory replay ledger (not durable), so it has no write permission to gate. Its package and handoff can be bound to a CNS verdict (section 8), so a verdict can be checked against the exact package it was about.

**Gate position.** TIE holds no gate position: it judges nothing and creates no CNS `GateResult`. `src/tie/cns_connector.py` only computes a digest of a package or handoff and checks (`binds`) that a verdict from some other gate was judged on exactly that content. The verdict comes from another repository's gate, so TIE is not on the ALPHA or OMEGA end of any chain.

## Role in the evidence spine

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
| [HERALD](https://github.com/wking53214/HERALD) | Upstream. TIE imports nothing from HERALD. It takes HERALD's signed export (Ed25519; version 4, or the older version 3 until 2027-03-31) and verifies it itself against the public keys the caller pins (`trusted_keys`). It does not accept a verifier function from the caller. |
| [Conservation_Kernel](https://github.com/wking53214/Conservation_Kernel) | Downstream in the spine. The CNS spine script's docstring states that no repository ships the step from TIE evidence to a kernel root; the script writes that step itself and builds the kernel with an evidence guard (`tie_evidence_guard`) that accepts only records TIE produced. Kernel source not checked. |
| [Governance_Gateway](https://github.com/wking53214/Governance_Gateway) | Downstream in the spine per the CNS script. TIE has no code that touches it. Its source was not checked. |
| [CCC](https://github.com/wking53214/CCC) | Last in the spine per the CNS script. TIE has no code that touches it. Its source was not checked. |
| [CNS](https://github.com/wking53214/CNS) | Shared-contract foundation. Holds shapes, not decisions. See the CNS interaction below. |
| [Link](https://github.com/wking53214/Link) | Not referenced by TIE source. No relationship established (Link's own source not checked). |
| [GEMS](https://github.com/wking53214/GEMS), [observe-perceive](https://github.com/wking53214/observe-perceive) | GEMS: the older `require_tie_adapter()` slot raises, but GEMS has a separate `TIEPackageSource` adapter that turns a TIE package into a GEMS artifact (checked in the GEMS repo, 2026-11-06, with tests there). observe-perceive: optional duck-typed adapter (`tie_governance_adapter.py`); does not import TIE (checked in the hub repo, 2026-11-07). |

```text
HERALD ──signed export──▶ TIE ──evidence records──▶ (caller-written step) ──▶ Conservation_Kernel ─▶ Governance_Gateway ─▶ CCC
 reads + extracts         records, refuses a            CNS spine script only                     (each judges its own door)
 claims                   changed or unverified export

CNS (optional; TIE's side is one-way, CNS's spine script also imports TIE): tie.cns_connector ─▶ cns.gate.subject_digest / GateResult.binds
CNS spine script (chains/evidence_spine.py) ─▶ imports tie.evidence.herald_intake
```

**Owns.** The shapes and invariants of a transcript evidence package; the rule that evidence from HERALD enters only through a verified export whose claims match the source text hash; the rule that a person's sign-off enters on its own path and is never taken for a machine reading; the digest of a TIE package or handoff.

**Does not own.** Whether a claim is true (HERALD judges the document and each claim; TIE records). Permission or admission of anything (Conservation_Kernel, Governance_Gateway and CCC judge their own doors; the receiver's own policy permits). HERALD's signing keys (the caller pins the trusted public keys; TIE verifies the signature itself). Persistence or a ledger (TIE writes nothing). Transcript extraction (no NLP, no model). Any CNS verdict: TIE can be named in one but never issues one.

**CNS interaction: PARTIAL.**
- Implemented, TIE side: an optional connector that makes a package or handoff nameable for a CNS verdict and checks a `cns.gate.GateResult` against it: `src/tie/cns_connector.py` (lazy `importlib` of `cns.gate`, the `subject_digest` function, and the `binds` function). Tested in `tests/test_cns_connector.py` and `tests/test_cns_independence.py` (CNS blocked).
- Implemented, CNS side: CNS's spine script imports TIE's intake (`herald_intake` in `chains/evidence_spine.py` in the CNS repo, and calls into it at several points; checked 2026-11-07 by reading the source, and run once that day, see the next section). That is CNS using TIE, not TIE using CNS.
- Absent: no TIE code imports `cns`, `cns_interop` or `cns_composition` at module load, and nothing in `src/tie` calls the connector. TIE issues no verdict, defines no gate, and has no UAI-1 signed-message code (checked by grep over `src`; the only `cns` references are in `cns_connector.py`).
- So the integration is binding only. A CNS verdict about a TIE package is possible to check, but nothing in TIE produces or requires one.

**Maturity and limitations.**
- 381 tests pass with CNS importable (1 skip: the schema tests, no `jsonschema` in that run); without CNS or `jsonschema`, 260 pass and 2 skip (see the table above for when, where and commit). One runtime dependency (`cryptography`).
- The package model is a reconstruction (`BUILD_STATUS.md`), not the historical TIE.
- Intake records `INFERRED` evidence only; it never produces `EXPLICIT`.
- The `routing_not_execution` check in `validate_package` (`src/tie/validation/validate.py`) checks shape and consistency only: a label like `review` passes, a sentence or a package and handoff that disagree fail. TIE cannot tell what a label means, and nothing in TIE reads the signal to act on it. Passing is not permission to run anything.
- Intake refuses unless the export is a signed HERALD export (version 4, or version 3 until `V3_SUNSET`, 2027-03-31) by a key in `trusted_keys`. The caller pins the keys; TIE checks the signature itself. A version 4 export also carries a signed handoff ID, signing time and audience: TIE refuses one addressed to someone else (`audience=`, default `"TIE"`), one signed more than `max_age_seconds` ago (default 24 hours) or in the future, and, if the caller calls `record_handoff_once(export, ledger)` once per accepted export, one it has already taken in. Intake never records anything on its own, so without that call and a ledger, replay is not detected. A ledger offers one atomic `claim_once(handoff_id)` (True for the first claim only), so two callers racing on the same ID cannot both succeed; if the ledger fails, the export is refused. `SeenHandoffs` is the in-memory ledger: safe across threads, but empty after a restart and invisible to other processes. A deployment that needs durability supplies its own `HandoffLedger` (a database unique key, an exclusive file create); TIE ships no storage. Each admitted claim's quoted text must also be exactly what the source holds at the claim's span (HERALD's convention: character offsets, start inclusive, end exclusive, no normalization); an empty, out-of-range, malformed or mismatching span refuses the whole export, on both the machine-reading and sign-off paths, and overlapping claims are allowed. The whole export is checked before any claim is processed: a malformed export, admitted list or claim, a wrongly typed `trusted_keys`, `audience`, `now` or `max_age_seconds` (a whole number from 1 to 1,000,000,000), ends in a refusal, never a Python error or a partial admission. Version 3 is accepted up to and including the sunset instant and refused after it. The signing time is the signer's own claim, not an independent clock. Version 3 has none of these and is accepted with a warning until the sunset, then refused. A version 2 export (in-process HMAC) is refused, because only the producing process could check it. Intake also refuses an export whose own `document.source_id` (or a claim's `source_id`) is not the source offered, so a genuine export cannot be taken in under a different name; refuses one that lists a claim ID, or the same claim, more than once; and, if the caller passes `expected_herald={"version": ..., "code_hash": ...}`, refuses one made by any other HERALD build. That build check reads the signer's own statement about itself: it catches an old or different build of an honest producer, not a signer who lies, and with no `expected_herald` any signed build is accepted.
- CNS is not on this path. HERALD signs and addresses the export; TIE checks the signature, audience, age, source text and structure itself, with `trusted_keys` and the ledger supplied by the caller. CNS does not sign, address or rewrite HERALD exports and has no receiver concept; it binds verdicts at later hops. `tests/test_cns_independence.py` pins that TIE intake needs no CNS.
- Replay protection is the caller's job, in this order: (1) verify and accept the export with `evidence_from_herald_export` and/or `signoffs_from_herald_export`; (2) hold the records; (3) call `record_handoff_once(export, ledger)` once; (4) pass the records on only after that call succeeds. Intake never claims anything itself. Two hazards are documented and tested: `record_handoff_once` verifies nothing unless you pass `trusted_keys` (then it checks signature, audience and age first, so a forged export cannot spend a real ID; without it, call it only with an export already accepted); and the claim is at-most-once, so a failure after it cannot be retried with the same ledger (a deployment wanting retry must keep its own record of work in progress and ask the producer for a fresh export, because a fresh export has a new handoff ID). Decided: TIE offers no release operation. A release would let a caller's mistake reopen replay for an export that was really used, and would move TIE toward holding state. Verification inside the claim is available by passing `trusted_keys` to `record_handoff_once`.
- No persistence, no key handling, no transport. The replay ledger that ships (`SeenHandoffs`) is in memory only: empty after a restart and invisible to other processes. A deployment that needs replay protection to survive a restart or span processes must supply its own `HandoffLedger` (one atomic `claim_once`).

## 8. Optional CNS Connection

TIE does not need CNS. An optional connector lets a CNS verdict be checked against the exact package it judged, and TIE's side is one-way; CNS's registry lists the link as two-way because CNS's spine script uses TIE's intake. Its only runtime dependency is `cryptography`, and nothing in the package imports CNS when it loads, and `tests/test_cns_independence.py` checks this with CNS blocked. `src/tie/cns_connector.py` is the one place that knows CNS exists. TIE is not published to PyPI. To use the connector, clone this repository and install it from the clone with the `cns` extra (`pip install -e '.[cns]'`); without CNS, asking for a digest raises `CnsNotInstalled` and nothing else changes.

**What is bound.** A `TIEPackage` (`package_content`, `package_digest`) or a `TypedHandoff` (`handoff_content`, `handoff_digest`), as plain deterministic data: the package id, the source (id, media type, title, provenance, and a SHA-256 and length of the transcript instead of the transcript), every coverage segment with its status and checksum, all evidence, artifacts, identity references and relationships, the reconstruction, the validation result, the knowledge views, the handoff, the routing signal and the build classification. `binds(result, obj)` says whether a `cns.gate.GateResult` was issued against exactly that output, using the subject labels `tie.package` and `tie.handoff`. A verdict about one package does not bind to another, nor to a package whose coverage says a different part of the source was read.

**Binding only, and why.** There is no gate, verdict mapping or chain here. TIE preserves before it interprets and does not judge, and its handoff stays data, not execution. Whether a package is good enough for anything is for the repository that issues the verdict. This only lets that verdict be checked against the package it was about.

Apache-2.0. Read `BUILD_STATUS.md` before relying on the ambition described in the other docs.
