# Typed Handoff

`TypedHandoff` carries objective, source identity, evidence IDs, artifact IDs, known uncertainty, routing signal, and provenance.

Routing is represented as data. No TIE code acts on the routing signal, so nothing downstream runs from it. The validation check that asserts this is hardcoded to pass (see `VALIDATION.md`), so it proves nothing by itself.
