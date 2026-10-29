"""Map source-timeline seconds onto the output timeline produced by cutting/concatenating segments."""
from __future__ import annotations

from typing import List, Optional, Tuple

from .schemas import Segment

MIN_SEGMENT = 0.25  # seconds; anything shorter is dropped


def normalize_segments(segments: List[Segment], duration: float) -> List[Segment]:
    """Clamp to [0, duration], drop empty/short ones, sort, merge overlaps."""
    cleaned: List[Tuple[float, float, str]] = []
    for s in segments:
        start = max(0.0, min(float(s.start), duration))
        end = max(0.0, min(float(s.end), duration))
        if end - start >= MIN_SEGMENT:
            cleaned.append((start, end, s.reason))
    cleaned.sort(key=lambda t: t[0])
    merged: List[Tuple[float, float, str]] = []
    for start, end, reason in cleaned:
        if merged and start <= merged[-1][1] + 0.05:  # touching/overlapping -> merge
            prev = merged[-1]
            merged[-1] = (prev[0], max(prev[1], end), prev[2] or reason)
        else:
            merged.append((start, end, reason))
    if not merged:
        merged = [(0.0, duration, "fallback: keep everything")]
    return [Segment(start=s, end=e, reason=r) for s, e, r in merged]


class Timeline:
    def __init__(self, segments: List[Segment]):
        self.segments = segments
        self._offsets: List[float] = []
        t = 0.0
        for s in segments:
            self._offsets.append(t)
            t += s.end - s.start
        self.output_duration = t

    def to_output(self, src_t: float) -> Optional[float]:
        """Return the output time for a source time, or None if it was cut."""
        for seg, off in zip(self.segments, self._offsets):
            if seg.start <= src_t <= seg.end:
                return off + (src_t - seg.start)
        return None

    def map_range(self, start: float, end: float) -> Optional[Tuple[float, float]]:
        """Clip a source range to the kept segments and map it. Returns None if fully cut."""
        best: Optional[Tuple[float, float]] = None
        for seg, off in zip(self.segments, self._offsets):
            lo, hi = max(start, seg.start), min(end, seg.end)
            if hi - lo > 0.05:
                out = (off + lo - seg.start, off + hi - seg.start)
                if best is None or (out[1] - out[0]) > (best[1] - best[0]):
                    best = out
        return best
