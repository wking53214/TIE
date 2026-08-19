from __future__ import annotations

from tie.models import Provenance, SourceRecord


def create_source(source_id: str, content: str, *, title: str | None = None, provenance: Provenance | None = None) -> SourceRecord:
    if not source_id.strip():
        raise ValueError("source_id must not be empty")
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    return SourceRecord(source_id=source_id, content=content, title=title, provenance=provenance or Provenance())
