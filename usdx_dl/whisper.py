"""Transcribe audio with `WhisperX <https://github.com/m-bain/whisperx>`_."""

import ast
import re
from pathlib import Path
from typing import Literal

import whisperx
from num2words import num2words
from whisperx.schema import SingleAlignedSegment, SingleSegment

from usdx_dl import lyrics
from usdx_dl.models import TranscribedData

__all__ = ["transcribe"]


def transcribe(
    audio_path: Path | str,
    lyrics_path: Path | str | None = None,
    model_arch: str = "turbo",
    device: str = "cpu",
    compute_type: Literal["int8", "float16", "float32"] | None = None,
    align_arch: str | None = None,
    keep_numbers: bool = False,
    progress: bool = True,
) -> tuple[str, list[TranscribedData]]:
    """Transcribe an audio file into word-level items.

    Args:
        audio_path: Path to the audio file. Preferably only vocals without music.
        lyrics_path: Path to a text file containing synced lyrics. If provided,
            these lyrics are used and aligned instead of running whisper to extract
            the lyrics.
        model_size: Model variant, e.g. "tiny", "large", "turbo", etc.
        device: Inference device name.
        compute_type: The data type to use. Not all devices support all types, e.g.
            float16 on CPU is typically not supported.
        align_arch: Alignment model variant. None to use the default.
        keep_numbers: Whether to keep numbers as digits (1, 2, 3, etc.) or replace
            them with words (one, two, three, etc.).
        progress: Whether to print progress during inference.

    Returns:
        Recognized language and words with timestamps.
    """
    audio_path = Path(audio_path)
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"

    model = whisperx.load_model(model_arch, device=device, compute_type=compute_type)
    audio = whisperx.load_audio(audio_path)
    if lyrics_path and Path(lyrics_path).exists():
        # use existing lyrics
        synced_lyrics = Path(lyrics_path).read_text(encoding="utf-8")
        segments = lyrics_to_segments(synced_lyrics)
        language = model.detect_language(audio)
    else:
        # predict lyrics
        result = model.transcribe(audio, print_progress=progress)
        segments = result["segments"]
        language = result["language"]

    model_align, metadata = whisperx.load_align_model(
        language_code=language, device=device, model_name=align_arch
    )

    if not keep_numbers:
        for obj in segments:
            obj["text"] = number_to_words(obj["text"], language)

    result = whisperx.align(
        segments,
        model_align,
        metadata,
        audio,
        device=device,
        return_char_alignments=False,
    )

    items: list[TranscribedData] = []
    segment: SingleAlignedSegment
    for segment in result["segments"]:
        for word in segment["words"]:
            items.append(
                TranscribedData(
                    word=word["word"] + " ",
                    start=word["start"],
                    end=word["end"],
                    score=word["score"],
                )
            )

    return language, items


def lyrics_to_segments(synced_lyrics: str) -> list[SingleSegment]:
    """Convert synced lyrics into whisperx format."""
    segments: list[SingleSegment] = []
    timestamp = 0.0
    for timestamp, text in lyrics.parse(synced_lyrics):
        if len(segments) > 0:
            segments[-1]["end"] = timestamp
        if text:
            segments.append(SingleSegment(start=timestamp, end=-1, text=text))
    return segments


def number_to_words(line, language: str = "en"):
    """Transcript words which do not contain characters in the alignment models
    dictionary e.g. "2014." or "£13.60" cannot be aligned and therefore are not
    given a timing. Therefore, convert numbers to words."""
    out_tokens = []
    in_tokens = re.findall(r"(\d+|\W+|\w+)", line)
    for token in in_tokens:
        try:
            num = ast.literal_eval(token)
            try:
                out_tokens.append(num2words(num, lang=language))
            except NotImplementedError:
                pass
        except Exception:  # pylint: disable=broad-exception-caught
            out_tokens.append(token)
    return "".join(out_tokens)
