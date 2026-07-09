"""Progress tracking for the download pipeline."""

import colorsys
import os
import sys
import time
from collections import deque
from collections.abc import Iterable, Iterator, Sized
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Literal, Self, TextIO, overload

import tqdm

from usdx_dl import __app__, flops, speedtest
from usdx_dl.models import (
    Config,
    Force,
    SeparatorModel,
    SongMetadata,
    SongPaths,
    WhisperModel,
)
from usdx_dl.types import ProgressCallback


class ProgressItem:
    """Helper class to track progress of a single step."""

    def __init__(self, callback: Callable[[], None], value: float = 0.0) -> None:
        self.value = value
        self.callback = callback

    @overload
    def __call__(self) -> float: ...

    @overload
    def __call__(self, value: float | int | bool) -> None: ...

    def __call__(self, value: float | int | bool | None = None) -> float | None:
        if value is None:
            return self.value

        value = min(max(float(value), 0.0), 1.0)
        if value != self.value:
            self.value = value
            self.callback()
        return None

    def __matmul__(self, other: tuple[float, float] | float) -> ProgressCallback:
        """`@ weight` to scale the progress value by a weight factor."""
        if isinstance(other, tuple):
            start, end = other
        else:
            start = 0
            end = float(other)
        if end <= start:
            raise ValueError("End value must be greater than start value.")
        if not 0 <= start <= 1 or not 0 <= end <= 1:
            raise ValueError("Start and end values must be between 0 and 1.")
        weight = end - start

        return lambda p: self(start + p * weight)


class ProgressEstimator:
    """Helper class to track progress of a download."""

    # TODO: track model download progress?

    # rough time estimates in seconds for a 3:30 min song on a 5 MB/s connection with
    # lyrics using demucs and whisperx-turbo on a AMD Ryzen 7 4800H
    WEIGHTS = {
        "cover": 0.2,
        "bg": 0.5,
        "video": 10,
        "audio": 2,
        "stem_split": 210,
        "denoise": 5,
        "transcription": 35,
        "pitch": 8,
        "generate_txt": 3,
    }
    REFERENCE_SONG_DURATION = 210  # seconds
    REFERENCE_NETWORK_SPEED = 5_000_000  # bytes/sec
    REFERENCE_WHISPER_MODEL = WhisperModel.TURBO
    REFERENCE_SEPARATOR_MODEL = SeparatorModel.DEMUCS
    REFERENCE_WHISPER_WEIGHT = 90  # seconds
    REFERENCE_FLOPS = 300 * 1e9
    WHISPER_ASR_SPEED = {
        # https://github.com/openai/whisper/discussions/2363
        WhisperModel.TINY: 34,
        WhisperModel.TURBO: 29,
        WhisperModel.BASE: 23,
        WhisperModel.SMALL: 13,
        WhisperModel.MEDIUM: 6.5,
        WhisperModel.LARGE: 3.5,
    }
    SEPARATOR_SPEED = {
        SeparatorModel.DEMUCS: 1.0,  # audio seconds per real-time seconds
        SeparatorModel.MEL_ROFORMER: 0.25,
    }
    DURATION_DEPENDENT = {
        "video",
        "audio",
        "stem_split",
        "denoise",
        "transcription",
        "pitch",
        "generate_txt",
    }
    NETWORK_DEPENDENT = {"cover", "bg", "video", "audio"}
    COMPUTE_INTENSIVE = {"stem_split", "transcription", "pitch"}
    GPU_ACCELERATED = {"stem_split", "transcription"}
    # NOTE: swift-f0 runs via onnxruntime on CPU

    def __init__(self, callback: ProgressCallback) -> None:
        self.cover = ProgressItem(self)
        self.bg = ProgressItem(self)
        self.video = ProgressItem(self)
        self.audio = ProgressItem(self)
        self.stem_split = ProgressItem(self)
        self.denoise = ProgressItem(self)
        self.transcription = ProgressItem(self)
        self.pitch = ProgressItem(self)
        self.generate_txt = ProgressItem(self)

        for step in self.WEIGHTS:
            assert hasattr(self, step), f"Missing ProgressItem for step: {step}"

        self.resetting: bool = False
        self.duration: float = 0.0  # seconds
        self.callback = callback
        self.network_speed = speedtest.download(
            num_bytes=10_000_000,
            cache_path=__app__.user_cache_path / "speedtest.down",
        )  # bytes/sec

    def reset(
        self,
        paths: SongPaths,
        song_meta: SongMetadata,
        force: Force | None,
        cfg: Config,
    ) -> None:
        """Reset progress tracker based on the current state of the pipeline."""
        self.resetting = True
        self.duration = song_meta.duration or self.REFERENCE_SONG_DURATION

        # NOTE: keep the following logic in sync with the steps in :func:`process`
        # set to 0 (False) if the step needs to be run, 1 (True) if it can be skipped
        self.cover(
            not (song_meta.cover_url and should_run(paths.cover, force, Force.DOWNLOAD))
        )
        self.bg(not (song_meta.bg_url and should_run(paths.bg, force, Force.DOWNLOAD)))
        self.video(
            not (not cfg.no_video and should_run(paths.video, force, Force.DOWNLOAD))
        )
        self.audio(not should_run(paths.audio, force, Force.DOWNLOAD))
        self.stem_split(not should_run(paths.vocals, force, Force.SPLIT_STEMS))
        if paths.song_orig_txt.exists():
            self.denoise.value = -1
            self.transcription.value = -1
            self.pitch.value = -1
            self.generate_txt.value = -1
        else:
            self.denoise(
                not (
                    should_run(paths.vocals_denoised, force, Force.DENOISE)
                    or should_run(paths.vocals_muted, force, Force.DENOISE)
                )
            )
            self.transcription(
                not should_run(paths.transcription, force, Force.TRANSCRIBE)
            )
            self.pitch(not should_run(paths.pitch, force, Force.PITCH))
            self.generate_txt(not should_run(paths.song_gen_txt, force, Force.TXT))
            if (
                cfg.no_lyrics
                or not paths.lyrics.exists()
                and self.transcription() < 1.0
            ):
                # account for whisper model choice:
                # - with lyrics: only alignment
                # - without lyrics: transcription + alignment
                ref_speed = self.WHISPER_ASR_SPEED[self.REFERENCE_WHISPER_MODEL]
                model_speed = self.WHISPER_ASR_SPEED.get(cfg.whisper_model, ref_speed)
                # NOTE: alignment model is always the same and already accounted for
                self.WEIGHTS["transcription"] += (
                    self.REFERENCE_WHISPER_WEIGHT * ref_speed / model_speed
                )

        # account for separator model choice
        ref_speed = self.SEPARATOR_SPEED[self.REFERENCE_SEPARATOR_MODEL]
        model_speed = self.SEPARATOR_SPEED.get(cfg.stem_model, ref_speed)
        self.WEIGHTS["stem_split"] *= ref_speed / model_speed

        # account for CPU vs GPU inference speed
        for step in self.COMPUTE_INTENSIVE:
            device_flops = (
                flops.GPU or flops.CPU  # fallback to CPU if GPU is not available
                if step in self.GPU_ACCELERATED
                else flops.CPU
            )
            self.WEIGHTS[step] *= self.REFERENCE_FLOPS / device_flops

        self.resetting = False

    def finish(self) -> None:
        """Mark all steps as finished."""
        self.resetting = True
        for step in self.WEIGHTS:
            getattr(self, step)(1.0)
        self.resetting = False
        self.callback(1.0)

    def calc(self) -> float:
        """Calculate overall progress as a float between 0.0 and 1.0."""
        progress = 0.0
        total_weight = 0.0
        for step, weight in self.WEIGHTS.items():
            step_progress = getattr(self, step)()
            if step_progress < 0.0:
                continue  # step is not applicable
            if step in self.DURATION_DEPENDENT and self.duration > 0:
                weight *= self.duration / self.REFERENCE_SONG_DURATION
            if step in self.NETWORK_DEPENDENT and self.network_speed > 0:
                weight *= self.REFERENCE_NETWORK_SPEED / self.network_speed
            progress += step_progress * weight
            total_weight += weight
        return progress / total_weight

    def __call__(self) -> None:
        """Call the callback with the current progress."""
        if not self.resetting:
            self.callback(self.calc())

    def __setattr__(self, name: str, value: Any) -> None:
        attr = getattr(self.__class__, name, None)
        if isinstance(attr, ProgressItem):
            value = min(max(float(value), 0.0), 1.0)
            attr(value)
        else:
            super().__setattr__(name, value)

    @contextmanager
    def from_tqdm(self, step: str, num: int = 1):
        """Monkey-patch tqdm to capture progress updates and update the given attribute
        with the overall progress.

        Args:
            step: The name of the attribute in this class to update with the progress.
            num: The number of expected subsequent progress bars. The total progress
                will be divided evenly among them. For example, if num=2, the first
                progress bar will contribute 0.0-0.5 to the overall progress, and the
                second will contribute 0.5-1.0.
        """
        assert step in self.WEIGHTS, f"Invalid step/attribute: {step}"
        i = 0
        pbar = self

        class patched_tqdm(tqdm.tqdm):  # pylint: disable=invalid-name,missing-class-docstring
            def update(self, n=1):
                if self.n == 0:
                    nonlocal i
                    i += 1
                super().update(n)
                progress = self.n / self.total / num + (i - 1) / num
                getattr(pbar, step)(progress)

        original_tqdm = tqdm.tqdm
        tqdm.tqdm = patched_tqdm  # type: ignore
        try:
            yield
        finally:
            tqdm.tqdm = original_tqdm  # type: ignore


def should_run(
    output_file: Path | str,
    force_arg: Force | None,
    *force_types: Force,
) -> bool:
    """Helper to only run certain parts of the pipeline of either the output file
    doesn't exist or the ``--force`` flag is set."""
    return not Path(output_file).exists() or force_arg in ("all", *force_types)


class BottomProgressBar[T]:
    """A progress bar that is always displayed at the bottom of the terminal,
    similar to e.g. the ``apt`` package manager.

    Example:
    >>> # standalone
    >>> bar = BottomProgressBar()
    >>> for i in range(101):
    >>>     bar(i / 100)
    >>>
    >>> # as an iterator
    >>> for item in BottomProgressBar(iterable, desc="Processing"):
    >>>     process(item)
    >>>
    >>> # as a context manager
    >>> with BottomProgressBar(desc="Processing") as bar:
    >>>     for item in iterable:
    >>>         process(item)
    """

    # ANSI escape codes for terminal control
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    SAVE_CURSOR_POS = "\0337"
    RESTORE_CURSOR_POS = "\0338"
    CLEAR_LINE = "\033[2K"
    MOVE_UP = "\033[%dA"
    MOVE_TO_ROW = "\033[%d;1H"
    FG_RGB = "\033[38;2;%d;%d;%dm"
    # cSpell: ignore DECSTBM
    DECSTBM = "\033[%d;%dr"  # set top and bottom margins

    def __init__(
        self,
        iterable: Iterable[T] | None = None,
        *,
        total: int | None = None,
        desc: str | None = None,
        title: str | None = None,
        ncols: int | Literal["auto"] = "auto",
        file: TextIO = sys.stdout,
        auto_clear: bool = True,
        pad: int = 1,
        ascii: bool = False,  # pylint: disable=redefined-builtin
        colors: bool = True,
    ) -> None:
        """
        Args:
            iterable: An optional iterable to wrap with the progress bar. If provided,
                the progress bar will automatically update as the iterable is consumed.
            total: The total number of items in the iterable. If not provided, it will be
                inferred from the iterable if possible.
            desc: An optional label to display before the progress bar.
            title: An optional title to display above the progress bar.
            ncols: The width of the progress bar in characters. If "auto", the width
                will be automatically determined based on the terminal size.
            file: The output stream to write the progress bar to.
            auto_clear: If True, the progress bar will be cleared from the terminal
                when it reaches 100%. If False, the progress bar will remain visible
                until :func:`clear` is called or the context manager exits.
            pad: The number of blank lines to leave above the progress bar.
            ascii: Whether to use Unicode or only ASCII characters.
            colors: Whether the progress bar should be colored or monochrome.
        """
        if pad < 0:
            raise ValueError("pad must be >= 0")

        self.iterable = iterable
        self.total = total
        self.desc = desc
        self.title = title
        self.ncols = ncols
        self.file = file
        self.auto_clear = auto_clear
        self.pad = pad
        self.ascii = ascii
        self.colors = colors

        if not self.total and isinstance(self.iterable, Sized):
            self.total = len(self.iterable)

        try:
            cols = os.get_terminal_size(file.fileno()).columns
        except OSError:
            cols = -1
        self._done = (
            # disable if the output is not a terminal, we can't determine the terminal
            # size, or the terminal is too small
            not file.isatty() or cols < 3
        )
        self._region_set = False
        self._reserved = 1 + self.pad + bool(self.title)
        self._rows = 0
        self._cols = 0
        self._start_time: float | None = None
        self._last_update_time: float | None = None
        self._debounce_interval = 0.1  # seconds between redraws

        # ETA estimator state
        self.eta_window_seconds = 30.0  # how far back "recent rate" looks
        self.eta_min_span_seconds = 0.5  # min span before trusting the recent rate
        self.eta_max_recent_weight = 0.85  # never fully discount the overall rate
        self.eta_display_smoothing = 0.3  # EMA factor for the displayed number
        self._progress_samples: deque[tuple[float, float]] = deque(maxlen=50)
        self._smoothed_eta: float | None = None

        if self.ascii:
            self.BLOCK = "#"
            self.EMPTY = "-"
        else:
            self.BLOCK = "█"
            self.EMPTY = "░"

    def __iter__(self) -> Iterator[T]:
        if self.iterable is None:
            raise TypeError(
                f"{self.__class__.__name__} was instantiated without an iterable, "
                "so it cannot be iterated over."
            )
        try:
            for i, item in enumerate(self.iterable, start=1):
                self(i / self.total if self.total else None)
                yield item
        finally:
            self.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        self.clear()
        return False

    def __call__(self, progress: float | None = None) -> None:
        self.update(progress)

    def _ensure_region(self) -> None:
        """(Re)configure the scroll region if this is the first call or the
        terminal has been resized."""
        try:
            cols, rows = os.get_terminal_size(self.file.fileno())
        except OSError:
            return  # unable to determine terminal size
        reserved = 1 + self.pad + bool(self.title)
        if (
            self._region_set
            and rows == self._rows
            and cols == self._cols
            and reserved == self._reserved
        ):
            return

        self._rows, self._cols = rows, cols
        self._reserved = reserved

        self.file.write("\n" * reserved)
        self.file.write(self.MOVE_UP % reserved)
        self.file.write(self.SAVE_CURSOR_POS)
        self.file.write(self.DECSTBM % (0, rows - reserved))  # set scroll margins
        self.file.write(self.RESTORE_CURSOR_POS)
        self.file.flush()

        self._region_set = True

    def _color(self, h: float, s: float = 1.0, l: float = 0.5) -> str:  # noqa: E741
        h = h % 1.0
        if self.colors:
            r, g, b = colorsys.hls_to_rgb(h, l, s)
        else:
            r = g = b = h
        return self.FG_RGB % (int(r * 255), int(g * 255), int(b * 255))

    def _time(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def _record_progress_sample(self, now: float, progress: float) -> None:
        """Record a (time, progress) sample for the rate estimator."""
        if self._progress_samples and progress < self._progress_samples[-1][1]:
            # progress went backwards (bar instance reused for a new task)
            # - the old samples no longer describe anything meaningful.
            self._progress_samples.clear()
            self._smoothed_eta = None

        self._progress_samples.append((now, progress))

        # drop samples that have fallen out of the window, but always keep at
        # least two so a rate can still be computed
        while (
            len(self._progress_samples) > 2
            and now - self._progress_samples[0][0] > self.eta_window_seconds
        ):
            self._progress_samples.popleft()

    def _estimate_eta(self, now: float, progress: float) -> str:
        if progress <= 0.0:
            return "ETA --:--"
        if progress >= 1.0:
            return "ETA 0:00"

        assert self._start_time is not None
        elapsed = now - self._start_time
        overall_rate = progress / elapsed if elapsed > 0 else 0.0

        recent_rate = None
        window_coverage = 0.0
        if len(self._progress_samples) >= 2:
            t_old, p_old = self._progress_samples[0]
            t_new, p_new = self._progress_samples[-1]
            span = t_new - t_old
            if span > self.eta_min_span_seconds:
                recent_rate = (p_new - p_old) / span
                window_coverage = min(span / self.eta_window_seconds, 1.0)

        if recent_rate is not None:
            # Lean on the overall average while the window is still filling (so the
            # very first couple of seconds aren't wildly noisy), then progressively
            # trust the recent, more reactive rate more - this is what lets the ETA
            # correct itself if the task speeds up or slows down partway through,
            # rather than being locked to the average from t=0.
            weight = self.eta_max_recent_weight * window_coverage
            rate = weight * recent_rate + (1 - weight) * overall_rate
        else:
            rate = overall_rate

        if rate <= 0:
            return "ETA --:--"

        instantaneous_eta = (1 - progress) / rate

        # Smooth the *displayed* number itself with an EMA on top of the
        # already-smoothed rate, so it doesn't visibly tick around frame to
        # frame even while the underlying estimate keeps adapting.
        if self._smoothed_eta is None:
            self._smoothed_eta = instantaneous_eta
        else:
            self._smoothed_eta += self.eta_display_smoothing * (
                instantaneous_eta - self._smoothed_eta
            )

        return f"ETA {self._time(max(0.0, self._smoothed_eta))}"

    def show(self) -> None:
        """Show the progress bar at 0%."""
        self.update(0.0)
        self._start_time = None
        self._last_update_time = None
        self._progress_samples.clear()

    def update(self, progress: float | None = None) -> None:
        """Update the progress bar with the given progress value in [0, 1]."""
        if self._done:
            return
        now = time.monotonic()
        if self._start_time is None:
            self._start_time = now

        if progress is not None:
            self._record_progress_sample(now, max(0.0, min(1.0, progress)))

        if (
            self._last_update_time is not None
            and now - self._last_update_time < self._debounce_interval
        ):
            return  # throttle redraws to at most 10 per second
        self._last_update_time = now

        self._ensure_region()

        if progress is not None:
            progress = max(0.0, min(1.0, progress))
            pct_text = f"{progress * 100:5.1f}% "
        else:
            pct_text = ""
        desc_part = f"{self.BOLD}{self.desc}{self.RESET} " if self.desc else ""

        elapsed = now - self._start_time
        if progress is None:
            eta_text = self._time(elapsed)
        else:
            eta_text = self._estimate_eta(now, progress)

        if progress is None:
            color = self._color(0.5, 1.0, 0.7)  # turquoise
        else:
            color = self._color(1 - 0.7 * progress, 1.0, 0.7)  # red->blue->green
        if progress is not None:
            desc_len = len(self.desc) + 1 if self.desc else 0
            overhead = desc_len + 2 + len(pct_text) + 1 + len(eta_text) + 1
            width = (
                self.ncols  #
                if isinstance(self.ncols, int)
                else max(5, self._cols - overhead)
            )
            filled = int(width * progress)
            bar_part = (
                color
                + self.BLOCK * filled
                + self.RESET
                + self.DIM
                + self.EMPTY * (width - filled)
                + self.RESET
            )
        else:
            # indeterminate progress bar (e.g. generator with unknown length)
            # -> fixed width with moving colors
            width = 8
            t = (now - self._start_time) * 0.25  # speed factor
            base_hue = -t % 1.0  # cycle through hue values
            hues = [(base_hue + i * 0.01) % 1.0 for i in range(width)]
            if not self.colors:
                hues = [1 - abs(hue * 2 - 1) for hue in hues]  # black->white->black
            bar_part = (
                "".join(self._color(h, 1.0, 0.7) + self.BLOCK for h in hues)
                + self.RESET
            )

        text = (
            f"{desc_part}"
            f"{self.DIM}[{self.RESET}{bar_part}{self.DIM}]{self.RESET} "
            f"{color}{pct_text}{self.RESET}{self.DIM}{eta_text}{self.RESET}"
        )

        self.file.write(self.SAVE_CURSOR_POS)
        if self.title:
            self.file.write(self.MOVE_TO_ROW % (self._rows - 1))
            self.file.write(self.CLEAR_LINE)
            self.file.write(f"{self.DIM}{self.title}{self.RESET}")
        self.file.write(self.MOVE_TO_ROW % self._rows)
        self.file.write(self.CLEAR_LINE)
        self.file.write(text)
        self.file.write(self.RESTORE_CURSOR_POS)
        self.file.flush()

        # auto-clear
        if progress and progress >= 1.0 and self.auto_clear:
            self.clear()

    def clear(self) -> None:
        """Clear the progress bar from the terminal and restore the scroll region."""
        if self._done or not self._region_set:
            return
        self._done = True
        self._region_set = False
        self.file.write(self.SAVE_CURSOR_POS)
        self.file.write(self.MOVE_TO_ROW % self._rows)
        self.file.write(self.CLEAR_LINE)
        self.file.write(self.DECSTBM % (1, self._rows))  # restore scroll region
        self.file.write(self.RESTORE_CURSOR_POS)
        self.file.flush()

    def set_description(self, desc: str | None) -> None:
        """Set the description text to display before the progress bar."""
        self.desc = desc
        self.update()

    def set_title(self, title: str | None) -> None:
        """Set the title text to display above the progress bar."""
        self.title = title
        self.update()
