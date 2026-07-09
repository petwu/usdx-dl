from pathlib import Path

import librosa
import soundfile as sf
from swift_f0 import SwiftF0

from usdx_dl.models import PitchedData

__all__ = ["detect_pitch"]


def detect_pitch(audio_path: Path | str) -> PitchedData:
    """Pitch detection using SwiftF0"""

    audio, sample_rate = sf.read(audio_path, dtype="float32")
    if len(audio.shape) > 1:
        audio = audio.T
    if audio.ndim > 1:
        audio = librosa.to_mono(audio)

    detector = SwiftF0(fmin=46.875, fmax=2093.75, confidence_threshold=0.9)
    result = detector.detect_from_array(audio, sample_rate)

    times = [float(t) for t in result.timestamps]
    frequencies = [float(f) for f in result.pitch_hz]
    confidence = [float(c) for c in result.confidence]

    return PitchedData(
        times=times,
        frequencies=frequencies,
        confidence=confidence,
    )
