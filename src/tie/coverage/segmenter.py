from __future__ import annotations

import hashlib
from typing import Iterable, Tuple

from tie.models import Coverage, CoverageSegment, CoverageStatus, SourceRecord


def _checked_ranges(not_inspected: Iterable[Tuple[int, int]], length: int):
    ranges = []
    for item in not_inspected:
        start, end = item
        if not (0 <= start < end <= length):
            raise ValueError(
                f"not_inspected range {(start, end)} must satisfy 0 <= start < end <= {length}"
            )
        ranges.append((start, end))
    return ranges


def segment_source(
    source: SourceRecord,
    *,
    max_chars: int = 4000,
    overlap: int = 0,
    not_inspected: Iterable[Tuple[int, int]] = (),
    declared_length: int | None = None,
) -> Coverage:
    """Split the source into segments and record what was and was not read.

    With no extra arguments every segment is INSPECTED, as before: the text
    given is the text read. The two optional arguments let the caller state
    what it knows was not read, and the record then says so instead of
    claiming the whole source:

    * ``not_inspected``: (start_char, end_char) ranges of ``source.content``
      the caller did not examine. Any segment that overlaps one is recorded
      NOT_INSPECTED, even if only partly, because a partly read segment
      cannot support a claim about the whole of it.
    * ``declared_length``: the length of the original source when
      ``source.content`` is a truncated copy of it. The characters beyond the
      copy are recorded as MISSING segments with no checksum, since there is
      no content to take one from.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")
    text = source.content
    if declared_length is not None and declared_length < len(text):
        raise ValueError("declared_length cannot be shorter than the content given")
    unread = _checked_ranges(not_inspected, len(text))
    absent = declared_length is not None and declared_length > len(text)

    segments: list[CoverageSegment] = []
    start = 0
    ordinal = 0
    while start < len(text) or (not text and ordinal == 0 and not absent):
        end = min(len(text), start + max_chars)
        chunk = text[start:end]
        checksum = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        skipped = any(s < end and start < e for s, e in unread)
        segments.append(CoverageSegment(
            segment_id=f"{source.source_id}:seg:{ordinal:04d}",
            ordinal=ordinal,
            start_char=start,
            end_char=end,
            status=CoverageStatus.NOT_INSPECTED if skipped else CoverageStatus.INSPECTED,
            source_id=source.source_id,
            checksum=checksum,
            notes=("overlaps a range the caller did not inspect",) if skipped else (),
        ))
        ordinal += 1
        if end >= len(text):
            break
        start = end - overlap

    if absent:
        start = len(text)
        while start < declared_length:
            end = min(declared_length, start + max_chars)
            segments.append(CoverageSegment(
                segment_id=f"{source.source_id}:seg:{ordinal:04d}",
                ordinal=ordinal,
                start_char=start,
                end_char=end,
                status=CoverageStatus.MISSING,
                source_id=source.source_id,
                checksum=None,
                notes=("beyond the content given; the source is longer than the copy",),
            ))
            ordinal += 1
            start = end
    return Coverage(source_id=source.source_id, segments=tuple(segments))
