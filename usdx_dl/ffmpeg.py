"""Utility functions to perform specific conversions/tasks with ffmpeg."""
# modified from https://github.com/rakuri255/UltraSinger

import subprocess
from pathlib import Path


def denoise_vocal_audio(
    input_path: Path | str,
    output_path: Path | str,
    mono: bool = False,
) -> bool:
    """Reduce noise from vocal audio with ffmpeg."""

    # Denoise audio samples with FFT:
    # - nr (noise reduction):
    #   Set the noise reduction in dB.
    #   Allowed range is 0.01 to 97, default value is 12 dB.
    # - nf (noise floor):
    #   Set the noise floor in dB.
    #   Allowed range is -80 to -20, default value is -50 dB.
    # - tn (track noise):
    #   Enable noise floor tracking. By default is disabled.
    #   With this enabled, noise floor is automatically adjusted.

    args = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-af",
        "afftdn=nr=70:nf=-80:tn=1",  # cSpell: disable-line
        *(["-ac", "1"] if mono else []),
        str(output_path),
    ]
    return subprocess.run(args, check=False).returncode == 0
