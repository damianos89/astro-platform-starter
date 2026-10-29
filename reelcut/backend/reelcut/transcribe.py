"""Speech-to-text with word timestamps.

Backends:
  whisper - faster-whisper running locally (CPU int8 by default; set REELCUT_WHISPER_DEVICE=cuda for GPU).
  mock    - deterministic fake transcript, used by the tests and for development without a model download.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import List, Optional

from .config import settings
from .schemas import Transcript, Word

log = logging.getLogger(__name__)

_model_lock = threading.Lock()
_model = None


def _whisper_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel  # heavy import, keep it lazy

            log.info("loading whisper model %s (%s/%s)", settings.whisper_model, settings.whisper_device, settings.whisper_compute_type)
            _model = WhisperModel(settings.whisper_model, device=settings.whisper_device, compute_type=settings.whisper_compute_type)
        return _model


def transcribe_whisper(wav: Path, duration: float, language: Optional[str]) -> Transcript:
    model = _whisper_model()
    segments, info = model.transcribe(
        str(wav),
        language=language or None,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        beam_size=5,
    )
    words: List[Word] = []
    for seg in segments:  # generator; transcription happens while iterating
        for w in seg.words or []:
            text = w.word.strip()
            if not text:
                continue
            words.append(Word(text=text, start=float(w.start), end=float(w.end)))
    return Transcript(language=info.language or (language or "de"), duration=duration, words=words)


_MOCK_SENTENCE = (
    "Hey Leute, heute zeige ich euch, wie ihr eure Reels in Sekunden schneiden lasst. "
    "Ähm, das Beste daran: die Untertitel kommen automatisch dazu, und zwar in einem richtig krassen Look. "
    "Also bleibt bis zum Ende dran, es lohnt sich wirklich."
).split()


def transcribe_mock(wav: Path, duration: float, language: Optional[str]) -> Transcript:
    """If `<wav>.words.json` exists it is loaded (list of {text,start,end}); otherwise words are spread evenly."""
    sidecar = wav.with_suffix(".words.json")
    if sidecar.exists():
        data = json.loads(sidecar.read_text())
        return Transcript(language=language or "de", duration=duration, words=[Word(**w) for w in data])
    words: List[Word] = []
    speech_end = duration * 0.9  # leave a silent tail so cutting has something to do
    pause = min(1.2, duration * 0.06)  # a thinking pause after every sentence, like real footage
    n_pauses = sum(1 for w in _MOCK_SENTENCE[:-1] if w.endswith("."))
    step = (speech_end - n_pauses * pause) / len(_MOCK_SENTENCE)
    t = 0.0
    for text in _MOCK_SENTENCE:
        words.append(Word(text=text, start=round(t, 3), end=round(t + step * 0.85, 3)))
        t += step + (pause if text.endswith(".") else 0.0)
    return Transcript(language=language or "de", duration=duration, words=words)


def transcribe(wav: Path, duration: float, language: Optional[str] = None) -> Transcript:
    backend = settings.transcribe_backend
    if backend == "mock":
        return transcribe_mock(wav, duration, language)
    if backend == "whisper":
        return transcribe_whisper(wav, duration, language)
    raise ValueError(f"unknown transcribe backend {backend!r}")
