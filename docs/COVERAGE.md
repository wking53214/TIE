# Coverage

Coverage records which source segments were inspected, not inspected, missing, or duplicates and preserves ordering plus character offsets for the reconstructed text-processing baseline.

The implementation does not claim complete historical coverage merely because processing finished.

What the segmenter records. By default the text given is the text read, so every segment is INSPECTED. A caller that knows part of the source was not read says so with `not_inspected` (character ranges; any segment they touch is NOT_INSPECTED) or `declared_length` (the source is longer than the copy; the remainder is MISSING, with no checksum). TIE does not find gaps on its own. A DUPLICATE status is described above but is not in the enum and is not produced.
