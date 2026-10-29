"""Turn a word-level transcript into an EditPlan.

The Claude backend asks the model for a structured EditPlan (cuts + mixed-design captions + enhancement
settings). The heuristic backend is a deterministic fallback for tests, offline use and as a safety net
when the API call fails.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from .config import settings
from .schemas import (
    Animation,
    Caption,
    CaptionSize,
    CaptionStyle,
    EditPlan,
    Enhance,
    FontFamily,
    JobRequest,
    Position,
    Segment,
    StylePreset,
    Transcript,
    Word,
)
from .timeline import Timeline, normalize_segments

log = logging.getLogger(__name__)

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_CAPTIONS = 400


class PlannerError(RuntimeError):
    pass


# --------------------------------------------------------------------------- prompt

SYSTEM_PROMPT = """You are a senior short-form video editor for TikTok and Instagram Reels.
You receive a word-level transcript (seconds, source timeline) of a raw vertical phone video and produce
an edit plan as structured JSON. You never see the pixels, so every decision is based on the spoken words
and timing.

CUTTING
- Keep the strongest hook in the first 1-2 seconds of the output. If the speaker rambles before the hook,
  cut the ramble.
- Remove filler words (ähm, äh, also..., like, you know), false starts, repeated takes and pauses longer
  than ~0.6 s. Cut on word boundaries: a segment starts a little before (≈0.08 s) a word's `start` and
  ends a little after (≈0.12 s) a word's `end`, so no word is clipped.
- Keep segments in chronological order unless re-ordering clearly improves the story. Never keep two
  overlapping segments.
- Respect the target duration (±15 %). If target is 0, keep everything that is worth keeping.

CAPTIONS (the on-screen subtitles)
- One caption = 2-5 words, exactly as spoken (fix obvious transcription errors, drop filler words).
- `start`/`end` are the first word's start and last word's end from the transcript. Captions must not
  overlap each other and must lie inside kept segments.
- `emphasis_words` are 0-2 words from `text` that carry the meaning (numbers, verbs, punchlines).
- Design per preset:
  * freestyle_mix: deliberately mixed look. Vary font family, size, position (lower/center/top), colours
    and animation between captions so it feels hand-made, but keep it readable: high contrast, max 2-3
    fonts over the whole clip, same style for 2-4 consecutive captions before switching, 'huge' only for
    punchlines. Use rotation_deg between -6 and 6 occasionally.
  * bold_pop: one heavy sans (bold_sans or condensed), uppercase, white fill, black outline, one accent
    colour for emphasis, animation pop, position lower.
  * clean: one calm style (bold_sans, medium, white, subtle outline, no rotation, animation none or pop),
    position lower. No emoji.
  * karaoke: bold_sans, large, animation typewriter on every caption, highlight colour for emphasis.
- Emoji: at most one per 3 captions and only when it adds meaning. '' otherwise.
- Keep the bottom 25 % and top 12 % of the screen in mind: 'lower' is the default safe spot.

ENHANCE
- denoise_audio/loudness_normalize true for phone footage. sharpen true unless the clip is probably
  already sharp. color_boost 0.2-0.5 for talking-head, up to 0.7 for outdoor/product shots. stabilize
  only if the user says the footage is shaky.

OUTPUT
- `title`: a punchy on-screen hook title (max 6 words) in the spoken language.
- `suggested_caption`: a ready-to-post caption with 3-6 relevant hashtags in the spoken language.
Follow the user's extra instructions when given; they override the defaults above.
"""


def _format_words(words: List[Word]) -> str:
    return "\n".join(f"[{w.start:.2f}-{w.end:.2f}] {w.text}" for w in words)


def _user_message(transcript: Transcript, request: JobRequest) -> str:
    target = "0 (editor's choice)" if request.target_duration <= 0 else f"{request.target_duration:.0f} s"
    instructions = request.instructions.strip() or "(none)"
    return (
        f"Source duration: {transcript.duration:.2f} s\n"
        f"Spoken language: {transcript.language}\n"
        f"Style preset: {request.preset.value}\n"
        f"Target duration: {target}\n"
        f"User instructions: {instructions}\n\n"
        f"Word-level transcript ({len(transcript.words)} words):\n{_format_words(transcript.words)}"
    )


# --------------------------------------------------------------------------- Claude backend


def plan_with_claude(transcript: Transcript, request: JobRequest) -> EditPlan:
    import anthropic

    client = anthropic.Anthropic()
    kwargs = dict(
        model=settings.claude_model,
        max_tokens=32000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _user_message(transcript, request)}],
        output_format=EditPlan,
        output_config={"effort": settings.claude_effort},
    )
    try:
        # Server-side refusal fallback: if a safety classifier declines, the API re-runs on a fallback model.
        with client.beta.messages.stream(
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
        ) as stream:
            message = stream.get_final_message()
    except anthropic.BadRequestError as exc:
        # Older proxies / platforms without the fallback feature: retry the plain request once.
        log.warning("beta request rejected (%s); retrying without fallbacks", exc.message)
        with client.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()

    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        raise PlannerError(f"Claude declined the request ({getattr(details, 'category', None)})")
    if message.stop_reason == "max_tokens":
        raise PlannerError("Claude's plan was truncated (max_tokens); try a shorter video")
    plan = message.parsed_output
    if plan is None:
        raise PlannerError("Claude returned no structured plan")
    usage = message.usage
    log.info(
        "plan from %s: %d segments, %d captions (in=%s cached=%s out=%s)",
        message.model,
        len(plan.keep_segments),
        len(plan.captions),
        usage.input_tokens,
        getattr(usage, "cache_read_input_tokens", 0),
        usage.output_tokens,
    )
    return plan


# --------------------------------------------------------------------------- heuristic backend

_FILLERS = {"ähm", "äh", "ähh", "hm", "hmm", "uh", "um", "uhm", "like,", "halt"}

_PALETTES = {
    StylePreset.freestyle_mix: [
        CaptionStyle(font=FontFamily.bold_sans, size=CaptionSize.large, fill_color="#FFFFFF", outline_color="#000000", highlight_color="#FFD400"),
        CaptionStyle(font=FontFamily.condensed, size=CaptionSize.huge, fill_color="#FFF200", outline_color="#1A1A1A", highlight_color="#FF2D55", rotation_deg=-4),
        CaptionStyle(font=FontFamily.rounded, size=CaptionSize.medium, fill_color="#111111", outline_color="#FFFFFF", highlight_color="#00C2FF", box=True, uppercase=False),
        CaptionStyle(font=FontFamily.serif, size=CaptionSize.large, fill_color="#FFFFFF", outline_color="#2B0A3D", highlight_color="#B6FF3B", italic=True, uppercase=False, rotation_deg=3),
        CaptionStyle(font=FontFamily.mono, size=CaptionSize.medium, fill_color="#00FF88", outline_color="#000000", highlight_color="#FFFFFF", box=True),
    ],
    StylePreset.bold_pop: [
        CaptionStyle(font=FontFamily.bold_sans, size=CaptionSize.large, fill_color="#FFFFFF", outline_color="#000000", highlight_color="#FFD400"),
    ],
    StylePreset.clean: [
        CaptionStyle(font=FontFamily.bold_sans, size=CaptionSize.medium, fill_color="#FFFFFF", outline_color="#000000", highlight_color="#FFFFFF", uppercase=False),
    ],
    StylePreset.karaoke: [
        CaptionStyle(font=FontFamily.bold_sans, size=CaptionSize.large, fill_color="#FFFFFF", outline_color="#000000", highlight_color="#FF2D55"),
    ],
}

_ANIMATIONS = {
    StylePreset.freestyle_mix: [Animation.pop, Animation.pop, Animation.slide_up, Animation.shake, Animation.pop, Animation.typewriter],
    StylePreset.bold_pop: [Animation.pop],
    StylePreset.clean: [Animation.none],
    StylePreset.karaoke: [Animation.typewriter],
}
_POSITIONS = {
    StylePreset.freestyle_mix: [Position.lower, Position.lower, Position.center, Position.lower, Position.top],
}


def plan_heuristic(transcript: Transcript, request: JobRequest) -> EditPlan:
    words = [w for w in transcript.words if w.text.lower().strip(".,!?") not in _FILLERS]
    if not words:
        return EditPlan(
            title="",
            summary="No speech detected; keeping the full clip without captions.",
            keep_segments=[Segment(start=0, end=transcript.duration, reason="no speech")],
            captions=[],
            enhance=Enhance(),
        )

    # 1) segments: split where the gap between words is > 0.7 s, pad a little around each run
    runs: List[List[Word]] = [[words[0]]]
    for prev, cur in zip(words, words[1:]):
        if cur.start - prev.end > 0.7:
            runs.append([cur])
        else:
            runs[-1].append(cur)
    segments = [
        Segment(start=max(0.0, r[0].start - 0.08), end=min(transcript.duration, r[-1].end + 0.12), reason="speech")
        for r in runs
    ]

    # 2) trim to target duration: drop whole runs from the end, then shorten the last run on a word boundary
    if request.target_duration > 0:
        target = request.target_duration
        total = sum(s.end - s.start for s in segments)
        while total > target * 1.15 and len(segments) > 1:
            dropped = segments.pop()
            total -= dropped.end - dropped.start
            runs.pop()
        if total > target * 1.1:
            last = segments[-1]
            new_end = last.end - (total - target)
            word_ends = [w.end + 0.12 for w in runs[-1] if last.start + 1.0 <= w.end + 0.12 <= new_end]
            end = max(word_ends) if word_ends else max(last.start + 1.0, new_end)
            segments[-1] = Segment(start=last.start, end=end, reason=last.reason)
            runs[-1] = [w for w in runs[-1] if w.end + 0.12 <= end]

    # 3) captions: 3-4 words each, styles rotate through the preset palette, same style for 3 captions
    palette = _PALETTES[request.preset]
    animations = _ANIMATIONS[request.preset]
    positions = _POSITIONS.get(request.preset, [Position.lower])
    captions: List[Caption] = []
    idx = 0
    for run in runs:
        i = 0
        while i < len(run):
            n = 4 if (idx % 2 == 0) else 3
            chunk = run[i : i + n]
            i += n
            text = " ".join(w.text for w in chunk)
            longest = max(chunk, key=lambda w: len(w.text.strip(".,!?")))
            emphasis = [longest.text] if len(longest.text) > 4 else []
            style = palette[(idx // 3) % len(palette)]
            captions.append(
                Caption(
                    start=chunk[0].start,
                    end=chunk[-1].end,
                    text=text,
                    emphasis_words=emphasis,
                    emoji="",
                    position=positions[(idx // 3) % len(positions)],
                    animation=animations[idx % len(animations)],
                    style=style,
                )
            )
            idx += 1

    title_words = [w.text.strip(".,!?") for w in words[:5]]
    return EditPlan(
        title=" ".join(title_words[:4]),
        summary="Heuristic plan: speech runs kept, long pauses and fillers removed.",
        keep_segments=segments,
        captions=captions,
        enhance=Enhance(),
        suggested_caption=" ".join(w.text for w in words[:12]) + " … #reels #tiktok #shorts",
    )


# --------------------------------------------------------------------------- validation


def sanitize_plan(plan: EditPlan, transcript: Transcript) -> EditPlan:
    """Make a model-produced plan safe to render: clamp times, fix colours, drop captions in cut parts."""
    segments = normalize_segments(plan.keep_segments, transcript.duration)
    timeline = Timeline(segments)

    captions: List[Caption] = []
    for cap in plan.captions[:MAX_CAPTIONS]:
        text = re.sub(r"\s+", " ", cap.text).strip()
        if not text or cap.end <= cap.start:
            continue
        if timeline.map_range(cap.start, cap.end) is None:
            continue
        style = cap.style.model_copy()
        for field in ("fill_color", "outline_color", "highlight_color"):
            if not _HEX.match(getattr(style, field) or ""):
                setattr(style, field, CaptionStyle.model_fields[field].default)
        emphasis = [e for e in cap.emphasis_words if e and e.lower().strip(".,!?") in text.lower()]
        captions.append(cap.model_copy(update={"text": text, "style": style, "emphasis_words": emphasis}))

    # Resolve overlaps: a caption ends where the next one starts.
    captions.sort(key=lambda c: c.start)
    for a, b in zip(captions, captions[1:]):
        if a.end > b.start:
            a.end = max(a.start + 0.1, b.start - 0.02)

    title = re.sub(r"\s+", " ", plan.title).strip()[:60]
    return plan.model_copy(update={"keep_segments": segments, "captions": captions, "title": title})


def make_plan(transcript: Transcript, request: JobRequest) -> EditPlan:
    backend = settings.planner_backend
    if backend == "heuristic":
        plan = plan_heuristic(transcript, request)
    elif backend == "claude":
        if not transcript.words:
            plan = plan_heuristic(transcript, request)
        else:
            plan = plan_with_claude(transcript, request)
    else:
        raise ValueError(f"unknown planner backend {backend!r}")
    return sanitize_plan(plan, transcript)
