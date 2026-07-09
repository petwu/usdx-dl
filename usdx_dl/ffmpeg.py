"""Utility functions to perform specific conversions/tasks with ffmpeg."""

import subprocess
from pathlib import Path

from usdx_dl.types import ProgressCallback


def run(
    *args: str,
    progress_callback: ProgressCallback | None = None,
) -> bool:
    """Run ffmpeg with the given arguments.

    Args:
        args: List of arguments to pass to ffmpeg.
        progress_callback: Optional callback function to report progress as a
            float between 0.0 and 1.0.

    Returns:
        True if ffmpeg ran successfully, False otherwise.
    """
    if not progress_callback:
        return subprocess.run(args, check=False).returncode == 0

    args_ = list(args)
    if args_ and not args_[0].lower().replace(".exe", "").endswith("ffmpeg"):
        args_.insert(0, "ffmpeg")
    args_.insert(1, "-progress")
    args_.insert(2, "pipe:1")
    input_file = None
    for i, arg in enumerate(args_):
        if arg == "-i" and i + 1 < len(args_):
            input_file = args_[i + 1]
            break
    if not input_file:
        raise ValueError("Input file not found in ffmpeg arguments.")
    total_secs = duration(input_file)
    progress = 0.0
    with subprocess.Popen(args_, stdout=subprocess.PIPE, text=True, bufsize=1) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            match key:
                case "progress":
                    if value == "end":
                        progress_callback(1.0)
                    else:
                        progress_callback(progress)
                case "out_time_ms":
                    progress = min(int(value) / 1_000_000 / total_secs, 1.0)

    rc = proc.wait()
    progress_callback(1.0)
    return rc == 0


def duration(path: Path | str) -> float:
    """Get the duration of a media file in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())


def denoise_vocal_audio(
    input_path: Path | str,
    output_path: Path | str,
    mono: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> bool:
    """Reduce noise from vocal audio with ffmpeg.

    See:
        https://github.com/rakuri255/UltraSinger/blob/main/src/modules/Audio/denoise.py
    """

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

    return run(
        "-y",
        "-i",
        str(input_path),
        "-af",
        "afftdn=nr=70:nf=-80:tn=1",  # cSpell: disable-line
        *(["-ac", "1"] if mono else []),
        str(output_path),
        progress_callback=progress_callback,
    )
