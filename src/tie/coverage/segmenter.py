from __future__ import annotations

import hashlib
from tie.models import Coverage, CoverageSegment, CoverageStatus, SourceRecord


def segment_source(source: SourceRecord, *, max_chars: int = 4000, overlap: int = 0) -> Coverage:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")
    text = source.content
    segments: list[CoverageSegment] = []
    start = 0
    ordinal = 0
    while start < len(text) or (not text and ordinal == 0):
        end = min(len(text), start + max_chars)
        chunk = text[start:end]
        checksum = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        segments.append(CoverageSegment(
            segment_id=f"{source.source_id}:seg:{ordinal:04d}",
            ordinal=ordinal,
            start_char=start,
            end_char=end,
            status=CoverageStatus.INSPECTED,
            source_id=source.source_id,
            checksum=checksum,
        ))
        ordinal += 1
        if end >= len(text):
            break
        start = end - overlap
    return Coverage(source_id=source.source_id, segments=tuple(segments))
