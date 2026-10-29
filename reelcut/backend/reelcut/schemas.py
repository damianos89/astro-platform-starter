"""Pydantic models shared by the API, the planner (Claude structured output) and the renderer.

Time values are seconds. EditPlan times always refer to the ORIGINAL (source) timeline;
the renderer maps them onto the cut output timeline (see timeline.py).
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- transcript


class Word(BaseModel):
    text: str
    start: float
    end: float


class Transcript(BaseModel):
    language: str = "de"
    duration: float
    words: List[Word]

    def text(self) -> str:
        return " ".join(w.text for w in self.words)


# --------------------------------------------------------------------------- request


class StylePreset(str, Enum):
    """What the user picks in the app. The planner turns this into concrete caption styles."""

    freestyle_mix = "freestyle_mix"  # the default: every caption may look different
    bold_pop = "bold_pop"  # big uppercase sans, 1 accent colour, word pops
    clean = "clean"  # one calm style, minimal animation
    karaoke = "karaoke"  # word-by-word highlight


class JobRequest(BaseModel):
    preset: StylePreset = StylePreset.freestyle_mix
    # Desired output length in seconds. 0 = let Claude decide (keep everything worth keeping).
    target_duration: float = Field(default=0, ge=0, le=600)
    # Free-text instructions from the user ("Hook am Anfang betonen", "keine Emojis", ...).
    instructions: str = ""
    # Spoken language hint for Whisper; "" = auto-detect.
    language: str = ""
    # Add an AI-generated hook title card for the first ~2 seconds.
    add_hook_title: bool = True


# --------------------------------------------------------------------------- edit plan (Claude output)


class FontFamily(str, Enum):
    bold_sans = "bold_sans"  # heavy grotesque, TikTok classic
    rounded = "rounded"  # friendly rounded sans
    condensed = "condensed"  # tall impact-like
    serif = "serif"  # editorial contrast
    mono = "mono"  # techy
    handwritten = "handwritten"  # casual script


class CaptionSize(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"
    huge = "huge"


class Position(str, Enum):
    top = "top"
    center = "center"
    lower = "lower"  # safe-zone above the TikTok/Instagram UI, the usual spot
    bottom = "bottom"


class Animation(str, Enum):
    none = "none"
    pop = "pop"  # scale-in
    slide_up = "slide_up"
    typewriter = "typewriter"  # karaoke-ish reveal per word
    shake = "shake"


class CaptionStyle(BaseModel):
    font: FontFamily = FontFamily.bold_sans
    size: CaptionSize = CaptionSize.large
    fill_color: str = Field(default="#FFFFFF", description="hex #RRGGBB")
    outline_color: str = Field(default="#000000", description="hex #RRGGBB")
    highlight_color: str = Field(default="#FFD400", description="hex #RRGGBB used for emphasised words")
    uppercase: bool = True
    box: bool = Field(default=False, description="draw an opaque box behind the text instead of an outline")
    italic: bool = False
    rotation_deg: float = Field(default=0, ge=-15, le=15, description="slight tilt for a freestyle look")


class Caption(BaseModel):
    start: float = Field(description="source-time seconds")
    end: float = Field(description="source-time seconds")
    text: str = Field(description="2-6 words, exactly as spoken (minor cleanup ok)")
    emphasis_words: List[str] = Field(default_factory=list, description="words from `text` to colour/scale up")
    emoji: str = Field(default="", description="optional single emoji appended to the line, '' for none")
    position: Position = Position.lower
    animation: Animation = Animation.pop
    style: CaptionStyle = Field(default_factory=CaptionStyle)


class Segment(BaseModel):
    start: float
    end: float
    reason: str = Field(default="", description="why this part is kept (hook, key point, punchline ...)")


class Enhance(BaseModel):
    denoise_audio: bool = True
    loudness_normalize: bool = True
    sharpen: bool = True
    color_boost: float = Field(default=0.3, ge=0, le=1, description="0 = untouched, 1 = very punchy")
    stabilize: bool = Field(default=False, description="two-pass vidstab, slow; only for shaky handheld footage")


class EditPlan(BaseModel):
    title: str = Field(description="short on-screen hook title, max 6 words")
    summary: str = Field(description="one sentence: what the clip is about and why the cut works")
    keep_segments: List[Segment] = Field(description="parts of the source to keep, in output order, non-overlapping")
    captions: List[Caption] = Field(description="caption lines in source time, each inside a kept segment")
    enhance: Enhance = Field(default_factory=Enhance)
    suggested_caption: str = Field(default="", description="post caption text for TikTok/Instagram incl. hashtags")


# --------------------------------------------------------------------------- job status


class JobStage(str, Enum):
    queued = "queued"
    probing = "probing"
    transcribing = "transcribing"
    planning = "planning"
    rendering = "rendering"
    done = "done"
    failed = "failed"


class JobStatus(BaseModel):
    id: str
    stage: JobStage
    progress: float = Field(ge=0, le=1)
    message: str = ""
    error: Optional[str] = None
    plan: Optional[EditPlan] = None
    result_url: Optional[str] = None
    output_duration: Optional[float] = None
