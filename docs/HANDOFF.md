# Typed Handoff

`TypedHandoff` carries objective, source identity, evidence IDs, artifact IDs, known uncertainty, routing signal, and provenance.

Routing is represented as data. No TIE code acts on the routing signal, so nothing downstream runs from it. The validation check `routing_not_execution` confirms the signal is a plain label (or absent) and that the package and handoff agree (see `VALIDATION.md`). It checks shape and consistency; it does not and cannot say what a label means, and passing is not permission to execute.
