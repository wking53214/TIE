# Validation

`validate_package` checks these conditions on a package:

- The source is present, and coverage refers to the same source.
- Every evidence record refers to that same source.
- A reconstruction cites evidence IDs.
- A claim that coverage is complete is honest (it needs segments to back it).
- A source with no inspected segments fails validation.

Partial coverage does not fail validation. It is reported as a warning and carried into the typed handoff. The routing check is hardcoded to pass (`src/tie/validation/validate.py`), so it cannot fail.

This is structural/conservation-oriented validation. It is not a claim that a historical reconstruction is true merely because its package validates.
