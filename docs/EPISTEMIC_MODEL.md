# Epistemic Model

TIE distinguishes epistemic status from build status.

`EXPLICIT`: directly supported by source material.

`INFERRED`: derived through reasoning from available evidence.

`UNKNOWN`: the available evidence is insufficient.

`CONFLICTED`: available evidence materially conflicts.

Confidence is intentionally not used as a substitute for epistemic status.

What intake currently produces: every claim admitted from a HERALD export is recorded as `INFERRED`, including claims a named person confirmed (those carry the origin `HUMAN_ACCEPTED_AI`). `EXPLICIT` is not produced by intake. The Transcript Extraction Gem uses a different label set; see `ARCHITECTURE.md`.
