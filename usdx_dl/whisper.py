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
from usdx_dl.types import ProgressCallback

__all__ = ["transcribe"]


def transcribe(
    audio_path: Path | str,
    lyrics_path: Path | str | None = None,
    model_arch: str = "turbo",
    device: str = "cpu",
    compute_type: Literal["int8", "float16", "float32"] | None = None,
    align_arch: str | None = None,
    keep_numbers: bool = False,
    print_progress: bool = True,
    progress_callback: ProgressCallback | None = None,
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
        progress_callback: Optional callback function to report progress as a float
            between 0.0 and 1.0.

    Returns:
        Recognized language and words with timestamps.
    """
    audio_path = Path(audio_path)
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"
    if progress_callback is None:
        progress_callback = lambda _: None  # noqa  # pylint: disable-all

    have_lyrics = lyrics_path and Path(lyrics_path).exists()
    if have_lyrics:
        # don't need a large model for language detection
        model_arch = "turbo"

    model = whisperx.load_model(model_arch, device=device, compute_type=compute_type)
    audio = whisperx.load_audio(audio_path)
    progress_callback(0.15)  # just rough estimates
    if have_lyrics:
        assert lyrics_path is not None
        # use existing lyrics
        synced_lyrics = Path(lyrics_path).read_text(encoding="utf-8")
        segments = lyrics_to_segments(synced_lyrics)
        language = model.detect_language(audio)
        progress_callback(0.20)
    else:
        # predict lyrics
        result = model.transcribe(
            audio,
            print_progress=print_progress,
            progress_callback=lambda progress: progress_callback(
                0.15 + 0.7 * progress / 100  # 15-85%
            ),
        )
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
        print_progress=print_progress,
        progress_callback=lambda progress: progress_callback(
            0.2 + 0.8 * progress / 100  # 20-100%
            if have_lyrics
            else 0.85 + 0.15 * progress / 100  # 85-100%
        ),
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

    progress_callback(1.0)

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
