# Compatibility boundaries and versioning recommendations

TIE is at `0.1.0`, unreleased and untagged. Nothing here is a release; it records what a consumer can and cannot rely on today, and what a first release would need.

## What a consumer depends on

| Contract | Where it lives | Stability today |
|---|---|---|
| Package and handoff shape | `schemas/tie_package.reconstructed.schema.json`, checked against real built packages (including one with every part filled in) in `tests/test_schema_conformance.py` | Reconstructed baseline, not the historical contract. May change before a release. |
| Package and handoff digests | `tie.cns_connector` binds every dataclass field | Adding, removing or renaming any field of `TIEPackage`, `TypedHandoff` or the records inside them changes digests of packages that exist today. Treat any model field change as a breaking change. |
| HERALD export intake | `tie.evidence.herald_intake` | Accepts export versions 4, and 3 until `V3_SUNSET` (2027-03-31, accepted up to and including that instant). Signing bytes are asserted against shared vectors in HERALD's tests and TIE's. |
| Replay ledger | `HandoffLedger.claim_once(handoff_id) -> bool` | The one atomic operation a durable ledger must offer. The older `has_seen` and `record` pair still works with a DeprecationWarning. |
| Routing signal | `ROUTING_LABEL` in `tie.validation.validate` | A label of letters, digits, dot, underscore, hyphen, starting with a letter, at most 64 characters. Tightening it would make packages that validate today fail. |
| Refusals | `HeraldIntakeRefused` | Every malformed export or bad setting ends here, not in a Python error. |

## What is not promised

- The schema does not enforce the routing label rule; `validate_package` does.
- `signed_at` is the signer's own claim, not an independent clock.
- The replay ledger that ships is in memory only. Durability is the deployment's.
- The historical TIE package contract and source code are not recovered.

## Versioning recommendation (for the owner to decide)

- Stay on `0.x` until the schema stops being labelled reconstructed. In `0.x`, a change to a model field, a digest, an export version accepted, or the routing label is a minor bump and is listed in a changelog; a bug fix is a patch.
- Move to `1.0.0` only when the package contract is declared (not reconstructed) and a consumer has used it.
- Keep CNS compatibility explicit: the `cns` extra pins one CNS tag, and a release should state which tag it was tested with.

## Removing version 3 support (after 2027-03-31)

1. Confirm no producer still sends version 3 (HERALD emits version 4 by default; version 3 needs an explicit legacy switch).
2. Delete the version 3 branch in `_check_identity` and `_ACCEPTED_VERSIONS`, and `V3_SUNSET`.
3. Remove the version 3 tests and the `herald_export.json` fixture only after a version 4 fixture covers each path they covered.
4. Update the README, this file and `BUILD_STATUS.md`; record it as a breaking change.

## Release-readiness checklist (nothing here has been done; no tag or release has been made)

- [ ] Owner decides the version number and the compatibility policy above.
- [ ] CI is green on the six matrix jobs and the `quality` job for the exact commit.
- [ ] Test counts in the README and `BUILD_STATUS.md` are re-measured at that commit.
- [ ] `tools/lint_baseline.json` is tightened to the current findings.
- [ ] A clean-environment install and import test passes (`pip install .`, import, run the tests).
- [ ] A changelog entry names every contract change since the last release.
