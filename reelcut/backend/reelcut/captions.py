"""EditPlan -> Advanced SubStation Alpha (.ass) file with mixed per-caption designs.

libass (via ffmpeg's `ass` filter) burns this into the video. Each distinct CaptionStyle becomes an ASS
style; per-caption animation, emphasis and placement are inline override tags.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .schemas import Animation, Caption, CaptionSize, CaptionStyle, EditPlan, FontFamily, Position
from .timeline import Timeline

# Font names are resolved by fontconfig on the render host. Override per family with
# REELCUT_FONT_BOLD_SANS=... etc. Defaults are common Debian/Ubuntu packages (see Dockerfile).
_DEFAULT_FONTS = {
    FontFamily.bold_sans: "Inter",
    FontFamily.rounded: "Comic Neue",
    FontFamily.condensed: "Liberation Sans Narrow",
    FontFamily.serif: "DejaVu Serif",
    FontFamily.mono: "DejaVu Sans Mono",
    FontFamily.handwritten: "Comic Neue",
}
EMOJI_FONT = os.environ.get("REELCUT_FONT_EMOJI", "Noto Color Emoji")

PLAY_W, PLAY_H = 1080, 1920

_SIZES = {CaptionSize.small: 56, CaptionSize.medium: 72, CaptionSize.large: 92, CaptionSize.huge: 118}
_MAX_CHARS_PER_LINE = {CaptionSize.small: 26, CaptionSize.medium: 20, CaptionSize.large: 16, CaptionSize.huge: 12}

# (ASS alignment \an, MarginV, y for \move) - numpad layout: 2 bottom-centre, 5 centre, 8 top-centre
_POSITIONS: Dict[Position, Tuple[int, int, int]] = {
    Position.top: (8, 260, 260),
    Position.center: (5, 0, PLAY_H // 2),
    Position.lower: (2, 430, PLAY_H - 430),
    Position.bottom: (2, 200, PLAY_H - 200),
}


def font_for(family: FontFamily) -> str:
    return os.environ.get(f"REELCUT_FONT_{family.value.upper()}", _DEFAULT_FONTS[family])


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    """'#RRGGBB' -> '&HAABBGGRR' (ASS stores colours as BGR with inverted alpha: 00 opaque, FF transparent)."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def escape_text(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\\", "/")


def wrap_text(words: List[str], max_chars: int) -> List[List[str]]:
    lines: List[List[str]] = [[]]
    for w in words:
        if lines[-1] and len(" ".join(lines[-1] + [w])) > max_chars:
            lines.append([w])
        else:
            lines[-1].append(w)
    return lines


@dataclass
class _StyleDef:
    name: str
    line: str


def _style_line(name: str, st: CaptionStyle, position: Position) -> str:
    align, margin_v, _ = _POSITIONS[position]
    size = _SIZES[st.size]
    if st.box:
        border_style, outline, shadow = 3, 18, 0
        back = ass_color(st.outline_color, alpha=0x20)
        outline_col = ass_color(st.outline_color, alpha=0x20)
    else:
        border_style, outline, shadow = 1, max(3, size // 18), max(2, size // 30)
        back = ass_color("#000000", alpha=0x80)
        outline_col = ass_color(st.outline_color)
    # SecondaryColour is the "not yet sung" colour for \k karaoke (typewriter animation).
    secondary = ass_color(st.fill_color, alpha=0xA0)
    fields = [
        name,
        font_for(st.font),
        str(size),
        ass_color(st.fill_color),
        secondary,
        outline_col,
        back,
        "-1",  # Bold
        "-1" if st.italic else "0",
        "0",  # Underline
        "0",  # StrikeOut
        "100",
        "100",  # ScaleX/Y
        "0",  # Spacing
        f"{st.rotation_deg:.1f}",  # Angle
        str(border_style),
        str(outline),
        str(shadow),
        str(align),
        "80",
        "80",  # MarginL/R
        str(margin_v),
        "1",  # Encoding
    ]
    return "Style: " + ",".join(fields)


def _animation_tags(anim: Animation, position: Position, duration_ms: int) -> str:
    _, _, y = _POSITIONS[position]
    x = PLAY_W // 2
    if anim == Animation.pop:
        return r"{\fscx70\fscy70\t(0,140,\fscx104\fscy104)\t(140,220,\fscx100\fscy100)}"
    if anim == Animation.slide_up:
        return rf"{{\move({x},{y + 70},{x},{y},0,180)\alpha&H60&\t(0,180,\alpha&H00&)}}"
    if anim == Animation.shake:
        return r"{\t(0,70,\frz2.5)\t(70,140,\frz-2.5)\t(140,210,\frz0)}"
    if anim == Animation.none:
        return ""
    return ""  # typewriter handled per word via \k


def _render_words(cap: Caption, size_px: int) -> str:
    """Inline text with emphasis colouring/sizing, line wrapping and optional karaoke timing."""
    st = cap.style
    words = cap.text.split()
    if st.uppercase:
        words = [w.upper() for w in words]
    emphasis = {e.lower().strip(".,!?") for e in cap.emphasis_words}
    lines = wrap_text(words, _MAX_CHARS_PER_LINE[st.size])

    karaoke = cap.animation == Animation.typewriter
    total_cs = max(10, int(round((cap.end - cap.start) * 100)))
    per_word_cs = max(5, total_cs // max(1, len(words)))

    hi_col = ass_color(st.highlight_color)
    base_col = ass_color(st.fill_color)
    out_lines: List[str] = []
    for line in lines:
        parts: List[str] = []
        for w in line:
            token = escape_text(w)
            pre = rf"{{\k{per_word_cs}}}" if karaoke else ""
            if w.lower().strip(".,!?") in emphasis:
                token = rf"{pre}{{\c{hi_col}\fs{int(size_px * 1.18)}}}{token}{{\c{base_col}\fs{size_px}}}"
            else:
                token = f"{pre}{token}"
            parts.append(token)
        out_lines.append(" ".join(parts))
    text = r"\N".join(out_lines)
    if cap.emoji:
        text += rf" {{\fn{EMOJI_FONT}}}{escape_text(cap.emoji)}"
    return text


def build_ass(plan: EditPlan, timeline: Timeline, hook_title: bool = True) -> str:
    """Return the full .ass document. Caption times are converted from source to output time."""
    styles: Dict[str, _StyleDef] = {}
    events: List[str] = []

    def style_name(st: CaptionStyle, pos: Position) -> str:
        key = st.model_dump_json() + pos.value
        if key not in styles:
            name = f"S{len(styles) + 1}"
            styles[key] = _StyleDef(name=name, line=_style_line(name, st, pos))
        return styles[key].name

    for cap in plan.captions:
        mapped = timeline.map_range(cap.start, cap.end)
        if mapped is None:
            continue
        start, end = mapped
        if end - start < 0.12:
            end = start + 0.12
        name = style_name(cap.style, cap.position)
        size_px = _SIZES[cap.style.size]
        duration_ms = int((end - start) * 1000)
        text = _animation_tags(cap.animation, cap.position, duration_ms) + _render_words(cap, size_px)
        events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{name},,0,0,0,,{text}")

    if hook_title and plan.title:
        title_style = CaptionStyle(
            font=FontFamily.condensed,
            size=CaptionSize.huge,
            fill_color="#FFFFFF",
            outline_color="#000000",
            highlight_color="#FFD400",
            box=True,
            uppercase=True,
        )
        name = style_name(title_style, Position.top)
        title_words = [escape_text(w.upper()) for w in plan.title.split()]
        text = r"\N".join(" ".join(l) for l in wrap_text(title_words, 12))
        anim = r"{\fscx80\fscy80\t(0,160,\fscx100\fscy100)\t(1700,2000,\alpha&HFF&)}"
        end = min(2.0, timeline.output_duration)
        events.append(f"Dialogue: 1,{ass_time(0)},{ass_time(end)},{name},,0,0,0,,{anim}{text}")

    header = [
        "[Script Info]",
        "Title: ReelCut captions",
        "ScriptType: v4.00+",
        f"PlayResX: {PLAY_W}",
        f"PlayResY: {PLAY_H}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
    ]
    header += [s.line for s in styles.values()]
    header += [
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    return "\n".join(header + events) + "\n"
