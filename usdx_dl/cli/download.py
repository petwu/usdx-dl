"""Subcommand: usdx-dl download - Download a song."""

import io
import logging
import re
import time
import uuid
from collections.abc import Iterable
from pathlib import Path
from time import perf_counter
from urllib.parse import quote_plus

import numpy as np
import requests
import soundfile as sf
from audio_separator.separator import Separator
from PIL import Image

from usdx_dl import (
    ansi,
    ffmpeg,
    fmt,
    hyphens,
    interactive,
    lyrics,
    models,
    silence,
    swift_f0,
    syllables,
    usdb,
    usdx,
    usdx_format,
    whisper,
    youtube,
)
from usdx_dl.models import (
    Force,
    PipelineContext,
    PitchedData,
    SeparatorModel,
    SongMetadata,
    SongPaths,
    TranscribedData,
    WhisperModel,
)
from usdx_dl.progress import BottomProgressBar, ProgressEstimator, should_run
from usdx_dl.types import ProgressCallback

__all__ = ["main", "Force"]


def main(source: str, **kwargs) -> None:
    """Args: See :func:`.args.parse`."""
    kwargs["prompt"] = interactive.CliPrompt()
    if Path(source).is_file():
        batch_process(Path(source), **kwargs)
    else:
        pbar = BottomProgressBar[None](desc="Processing")
        pbar.show()
        kwargs["progress_callback"] = pbar
        kwargs.pop("keep_going", None)
        run_pipeline(url_or_id=source, **kwargs)


def batch_process(
    batch_path: Path,
    keep_going: bool,
    **kwargs,
) -> None:
    """Args: See :func:`.args.parse`."""
    __print_batch_status(f"Processing from: {batch_path}")
    skipped: list[str] = []
    while True:
        batch = __load_batch_file(batch_path)
        __print_batch_status(
            f"{len(batch)} {fmt.pluralize(len(batch), 'item')} remaining."
        )
        if len(batch) == 0:
            if not keep_going:
                break
            __print_batch_status("Batch file is empty. Waiting for new entries ...")
            while len(batch) == 0:
                time.sleep(3)
                batch = __load_batch_file(batch_path)
        url_or_id = batch.pop(0).strip()
        __print_batch_status(f"Processing {url_or_id} ...")
        try:
            run_pipeline(url_or_id=url_or_id, **kwargs)
        except KeyboardInterrupt:
            __print_batch_status("Interrupted by user. Stopping.")
            return
        except Exception as e:  # pylint: disable=broad-exception-caught
            __print_batch_status(f"Failed to process {url_or_id}. Skipping. Error: {e}")
            skipped.append(url_or_id)
        remaining = __load_batch_file(batch_path)
        remaining.remove(url_or_id)
        __save_batch_file(batch_path, remaining)
    __print_batch_status("Finished.")
    if len(skipped) == 0:
        __save_batch_file(batch_path, [])
    else:
        __print_batch_status(
            f"Keeping {len(skipped)} skipped {fmt.pluralize(len(skipped), 'item')}."
        )
        __save_batch_file(batch_path, skipped)


def __load_batch_file(path: Path) -> list[str]:
    batch = path.read_text(encoding="utf-8").splitlines()
    batch = list(filter(None, (line.strip() for line in batch)))
    return batch


def __save_batch_file(path: Path, batch: Iterable[str]) -> None:
    path.write_text("\n".join(batch) + "\n", encoding="utf-8")


def __print_batch_status(msg: str) -> None:
    print(f"{ansi.MAGENTA}[BATCH] {msg}{ansi.RESET}", flush=True)


def ctx_uuid() -> str:
    """Generate a unique ID for the pipeline context."""
    return str(uuid.uuid4())


def run_pipeline(
    url_or_id: str,
    usdb_cookie: str | None,
    output_dir: Path,
    stem_model: SeparatorModel,
    whisper_model: WhisperModel,
    sample_rate: int,
    vocals_gain: float,
    phrase_correction: float,
    force: Force | None,
    no_lyrics: bool,
    no_video: bool,
    non_interactive: bool,
    prompt: interactive.Prompt,
    progress_callback: ProgressCallback = lambda progress: None,
) -> None:
    """Args: See :func:`.args.parse`."""
    ctx = PipelineContext(
        uuid=ctx_uuid(),
        url_or_id=url_or_id,
        sample_rate=sample_rate,
        vocals_gain=vocals_gain,
        phrase_correction=phrase_correction,
        force=force,
        non_interactive=non_interactive,
    )
    cfg_override = models.Config(
        usdb_cookie=usdb_cookie,
        stem_model=stem_model,
        whisper_model=whisper_model,
        no_lyrics=no_lyrics,
        no_video=no_video,
    )
    prepare(ctx, output_dir, cfg_override, prompt)
    process(ctx, output_dir, cfg_override, progress_callback)


def prepare(
    ctx: PipelineContext,
    output_dir: Path,
    cfg_override: models.Config | None = None,
    prompt: interactive.Prompt | None = None,
) -> None:
    """Prepare a download request by collecting necessary metadata."""
    cfg = models.Config.load()
    if cfg_override:
        cfg.merge_(cfg_override, override=True)
    if prompt is None:
        prompt = interactive.NonInteractivePrompt()

    # detect if we start from USDB or YouTube
    if "usdb.animux.de" in ctx.url_or_id or ctx.url_or_id.isdigit():
        if not cfg.usdb_cookie:
            if ctx.non_interactive:
                raise RuntimeError(
                    "Cannot continue without the PHPSESSID cookie from "
                    f"{usdb.APIClient.URL}."
                )
            print(f"PHPSESSID cookie is required to access {usdb.APIClient.URL}.")
            sessions = usdb.find_sessions()
            if sessions:
                choice = prompt.choice(
                    f"Found {len(sessions)} logged in browser session(s) for USDB. ",
                    description="Select one to use, or enter a custom PHPSESSID cookie.",
                    choices=[
                        f"{s.cookie} "
                        f"from {ansi.MAGENTA}{s.browser}{ansi.RESET} "
                        f"logged in as {ansi.CYAN}{s.username}{ansi.RESET}"
                        for s in sessions
                    ]
                    + ["Other (manual entry)"],
                )
                if choice < len(sessions):
                    cfg.usdb_cookie = sessions[choice].cookie
                    cfg.save()
            if not cfg.usdb_cookie:
                usdb_cookie = prompt.string("PHPSESSID")
                if len(usdb_cookie.replace("PHPSESSID=", "")) < 22:
                    raise ValueError(
                        "Invalid PHPSESSID, must be at least 22 characters."
                    )
                cfg.usdb_cookie = usdb_cookie
                cfg.save()
        usdb_client = usdb.APIClient(ctx.url_or_id, cfg.usdb_cookie)
        yt_client = None
        song_id = str(usdb_client.id)
    elif "youtube.com" in ctx.url_or_id or re.match(r"^[\w_-]{11}$", ctx.url_or_id):
        usdb_client = None
        yt_client = youtube.APIClient(ctx.url_or_id)
        song_id = yt_client.id
    else:
        raise ValueError(f"Invalid URL or ID: {ctx.url_or_id}")

    # output paths
    ctx.song_id = song_id
    paths = SongPaths(output_dir, ctx.song_id)
    paths.mkdirs()
    if ctx.force == Force.CLEAN and paths.base_dir.exists():
        paths.clean()

    if usdb_client is not None:
        __print_step("Downloading TXT from USDB")
        t = perf_counter()
        # download lyrics/txt file from USDB
        if should_run(paths.song_orig_txt, ctx.force, Force.DOWNLOAD):
            txt = usdb_client.fetch_txt()
            if txt is None:
                cfg.usdb_cookie = None
                cfg.save()
                raise RuntimeError(f"Failed to fetch TXT for {ctx.url_or_id}")
            paths.song_orig_txt.write_text(txt, "utf-8")
            __print_time(perf_counter() - t)
        else:
            txt = paths.song_orig_txt.read_text("utf-8")
            __print_cached(paths.song_orig_txt)

        # parse metadata
        song_meta = usdx_format.parse_metadata(txt)
        if song_meta is None:
            raise RuntimeError("Failed to parse USDX metadata.")
        song_meta.usdb_url = usdb_client.url
        song_meta.cover_url = usdb_client.cover_url()

        # find related YouTube video
        yt_id = usdb_client.search_youtube_link()
        if yt_id is not None:
            yt_client = youtube.APIClient(yt_id)
        else:
            yt_client = youtube.search(f"{song_meta.artist} {song_meta.title}")
        song_meta.video_url = yt_client.url

    else:
        assert yt_client is not None
        song_meta = None

    __print_step("Collecting song metadata")
    t = perf_counter()
    if should_run(paths.meta, ctx.force, Force.DOWNLOAD):
        yt_meta = yt_client.get_metadata()
        if song_meta is None:
            song_meta = yt_meta
        else:
            song_meta.merge_(yt_meta)
        if not ctx.non_interactive:
            print("Please check the following metadata:")
            song_meta.artist = prompt.string("Artist", default=song_meta.artist)
            song_meta.title = prompt.string("Title", default=song_meta.title)
            if usdb_client is not None:
                new_video_url = prompt.string(
                    "YouTube URL",
                    default=song_meta.video_url,
                    description=yt_client.describe(),
                )
                if new_video_url != song_meta.video_url:
                    yt_client = youtube.APIClient(new_video_url)
                    song_meta.video_url = yt_client.url
                    yt_meta = yt_client.get_metadata()
                    song_meta.bg_url = yt_meta.bg_url
                    if yt_client.is_youtube_url(song_meta.cover_url):
                        song_meta.cover_url = yt_meta.cover_url
        else:
            ctx.reviewed = False
        models.to_json(song_meta, paths.meta)
        __print_time(perf_counter() - t)
    else:
        song_meta = models.from_json(SongMetadata, paths.meta)
        __print_cached(paths.meta)
    ctx.meta = song_meta
    print(song_meta)

    # find lyrics
    if not paths.song_orig_txt.exists() and not cfg.no_lyrics:
        __print_step("Downloading lyrics")
        t = perf_counter()
        if should_run(paths.lyrics, ctx.force, Force.DOWNLOAD):
            lyrics_sync = lyrics.search(song_meta.artist, song_meta.title, synced=True)
            if lyrics_sync is None:
                print("No lyrics found.")
                if not ctx.non_interactive:
                    google_url = "https://www.google.com/search?q=" + quote_plus(
                        f'{song_meta.artist} {song_meta.title} lyrics "lrc"'
                    )
                    print(f"Search for them on Google: {google_url}")
                    lyrics_sync = prompt.multiline(
                        "Then paste the synched lyrics (LRC format) here "
                        "[empty to skip]."
                    )
                    if lyrics_sync.count("\n") >= 10:
                        paths.lyrics.write_text(lyrics_sync, "utf-8")
                    else:
                        print("- skip -")
                else:
                    ctx.reviewed = False
            else:
                if not ctx.non_interactive:
                    print(lyrics_sync)
                    if prompt.yes_no("Lyrics correct?", default=True):
                        paths.lyrics.write_text(lyrics_sync, "utf-8")
                    else:
                        lyrics_sync = None
                else:
                    ctx.reviewed = False

            __print_time(perf_counter() - t)
        else:
            lyrics_sync = paths.lyrics.read_text("utf-8")
            __print_cached(paths.lyrics)

        ctx.lyrics = lyrics_sync


def update_metadata(ctx: PipelineContext, output_dir: Path) -> SongMetadata:
    """Update song metadata with user changes."""
    # merge user changes into metadata
    paths = SongPaths(output_dir, ctx.song_id)
    if not ctx.song_id or not paths.meta.exists():
        raise RuntimeError("PipelineContext is not properly initialized.")
    song_meta = models.from_json(SongMetadata, paths.meta)

    # check if video URL has changed and we need to update the background/cover images
    video_changed = ctx.meta and ctx.meta.video_url != song_meta.video_url
    song_meta.merge_(ctx.meta, override=True)
    if song_meta.video_url is None:
        raise RuntimeError(f"Failed to find YouTube for {ctx.url_or_id}.")
    if video_changed:
        yt_client = youtube.APIClient(song_meta.video_url)
        yt_meta = yt_client.get_metadata()
        song_meta.bg_url = yt_meta.bg_url
        if yt_client.is_youtube_url(song_meta.cover_url):
            song_meta.cover_url = yt_meta.cover_url

    # check if the lyrics have changed
    if ctx.lyrics:
        current_lyrics = (
            paths.lyrics.read_text("utf-8") if paths.lyrics.exists() else ""
        )
        if current_lyrics != ctx.lyrics:
            paths.lyrics.write_text(ctx.lyrics, "utf-8")

    models.to_json(song_meta, paths.meta)
    return song_meta


def process(
    ctx: PipelineContext,
    output_dir: Path,
    cfg_override: models.Config | None = None,
    progress_callback: ProgressCallback = lambda progress: None,
) -> None:
    """Process the song using the pipeline context. This function assumes that the
    pipeline context has been properly initialized by :func:`prepare`."""
    cfg = models.Config.load()
    if cfg_override:
        cfg.merge_(cfg_override, override=True)

    __print_step("Starting processing pipeline")
    if not ctx.song_id:
        raise RuntimeError("PipelineContext is not properly initialized.")
    paths = SongPaths(output_dir, ctx.song_id)
    print(f"Saving files to {paths.base_dir}")
    # context values take precedence over saved values
    if ctx.meta:
        models.to_json(ctx.meta, paths.meta)
        song_meta = ctx.meta
    elif paths.meta.exists():
        song_meta = models.from_json(SongMetadata, paths.meta)
    else:
        raise RuntimeError("PipelineContext is not properly initialized.")
    if song_meta.video_url is None:
        raise RuntimeError(f"Failed to find YouTube for {ctx.url_or_id}.")
    yt_client = youtube.APIClient(song_meta.video_url)
    # create empty file to make the name visible in file explorers
    paths.name_path(song_meta.artist, song_meta.title).touch()

    if ctx.lyrics:
        paths.lyrics.write_text(ctx.lyrics, "utf-8")

    # initialize progress tracker
    progress = ProgressEstimator(progress_callback)
    progress.reset(paths, song_meta, ctx.force, cfg)
    if hasattr(progress_callback, "set_title"):
        progress_callback.set_title(str(song_meta))  # type: ignore

    # download cover image
    __print_step("Downloading cover and background image")
    t = perf_counter()
    chunk_size = 8192
    if song_meta.cover_url and should_run(paths.cover, ctx.force, Force.DOWNLOAD):
        with requests.get(song_meta.cover_url, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            if total_size > 0:
                buf = io.BytesIO()
                for chunk in response.iter_content(chunk_size):
                    buf.write(chunk)
                    progress.cover(buf.tell() / total_size)
            else:
                buf = io.BytesIO(response.content)
        cover = Image.open(buf)
        crop_size = min(cover.width, cover.height)
        left = (cover.width - crop_size) // 2
        top = (cover.height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        with open(paths.cover, "wb") as f:
            cover.crop((left, top, right, bottom)).save(f)
        if not song_meta.bg_url:
            __print_time(perf_counter() - t)
    elif song_meta.cover_url:
        __print_cached(paths.cover)
    else:
        print("No cover found.")
    progress.cover(True)
    if song_meta.bg_url and should_run(paths.bg, ctx.force, Force.DOWNLOAD):
        with requests.get(song_meta.bg_url, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            if total_size > 0:
                buf = io.BytesIO()
                for chunk in response.iter_content(chunk_size):
                    buf.write(chunk)
                    progress.bg(buf.tell() / total_size)
            else:
                buf = io.BytesIO(response.content)
        background = Image.open(buf)
        with open(paths.bg, "wb") as f:
            background.save(f)
        __print_time(perf_counter() - t)
    else:
        __print_cached(paths.bg)
    progress.bg(True)

    # download audio/video from YouTube
    t = perf_counter()
    if cfg.no_video:
        __print_step("Downloading audio from YouTube")
    else:
        __print_step("Downloading video and audio from YouTube")
        if should_run(paths.video, ctx.force, Force.DOWNLOAD):
            ok = yt_client.download_video(paths.video, progress_callback=progress.video)
            if not ok:
                raise RuntimeError(f"Failed to download YouTube video: {yt_client.url}")
        else:
            __print_cached(paths.video)
    if should_run(paths.audio, ctx.force, Force.DOWNLOAD):
        ok = yt_client.download_audio(
            paths.audio, ctx.sample_rate, progress_callback=progress.audio
        )
        if not ok:
            raise RuntimeError(f"Failed to download YouTube video: {yt_client.url}")
        __print_time(perf_counter() - t)
    else:
        __print_cached(paths.audio)
    progress.audio(True)

    # split vocals using AI model
    __print_step(f"Splitting vocals and instrumental parts using {cfg.stem_model}")
    t = perf_counter()
    if should_run(paths.vocals, ctx.force, Force.SPLIT_STEMS):
        separator = Separator(
            log_level=logging.INFO,
            output_dir=paths.tmp_dir.as_posix(),
            output_format=paths.vocals.suffix[1:],
            sample_rate=sf.info(paths.audio).samplerate,
        )
        model_name_mapping = {
            # cSpell: disable
            SeparatorModel.DEMUCS: "htdemucs.yaml",
            SeparatorModel.MEL_ROFORMER: "mel_band_roformer_karaoke_becruily.ckpt",
            # cSpell: enable
        }
        separator.load_model(model_name_mapping[cfg.stem_model])
        output_names = {
            "Vocals": "vocals",
            "Instrumental": "instrumental",
            "Drums": "drums",
            "Bass": "bass",
            "Other": "other",
        }
        shifts = getattr(separator.model_instance, "shifts", 1)
        with progress.from_tqdm("stem_split", num=shifts):
            separator.separate(paths.audio.as_posix(), output_names)
        tmp_vocals = paths.tmp_dir / f"vocals.{paths.vocals.suffix[1:]}"
        if not tmp_vocals.exists():
            raise RuntimeError(
                f"Failed to separate vocals: {tmp_vocals} not found. "
                "audio-separator may fail without an exception. "
                "Please look at the output/logs for more information."
            )
        if paths.vocals.exists():
            paths.vocals.unlink()
        tmp_vocals.rename(paths.vocals)
        stem_names_map = {
            SeparatorModel.DEMUCS: ["drums", "bass", "other"],
        }
        if stem_names := stem_names_map.get(cfg.stem_model):
            stem_paths = [
                paths.tmp_dir / f"{stem}.{paths.vocals.suffix[1:]}"
                for stem in stem_names
            ]
            stems = [sf.read(p) for p in stem_paths]
            assert all(sr == ctx.sample_rate for _, sr in stems), (
                f"Sample rates don't match: {[sr for _, sr in stems]}"
            )
            instrumental = sum(data for data, _ in stems)
            instrumental = np.clip(instrumental, -1.0, 1.0)
            sf.write(paths.instrumental, instrumental, ctx.sample_rate)  # type: ignore
            for p in stem_paths:
                p.unlink()

        __print_time(perf_counter() - t)
    else:
        __print_cached(paths.vocals)
        __print_cached(paths.instrumental)
    progress.stem_split(True)

    if ctx.vocals_gain > 0:
        vocals, _ = sf.read(paths.vocals)
        instrumental, _ = sf.read(paths.instrumental)
        instrumental_plus_vocals = instrumental + ctx.vocals_gain * vocals
        paths.instrumental = paths.instrumental.with_stem(
            paths.instrumental.stem + f"_{ctx.vocals_gain}x_vocals"
        )
        sf.write(paths.instrumental, instrumental_plus_vocals, ctx.sample_rate)

    if paths.song_orig_txt.exists():
        txt = paths.song_orig_txt.read_text("utf-8")
    else:
        # preprocess vocals audio
        __print_step("Denoising vocals stem")
        t = perf_counter()
        if should_run(paths.vocals_denoised, ctx.force, Force.DENOISE) or should_run(
            paths.vocals_muted, ctx.force, Force.DENOISE
        ):
            ok = ffmpeg.denoise_vocal_audio(
                paths.vocals,
                paths.vocals_denoised,
                mono=True,
                # ~25% of denoise step is ffmpeg processing
                progress_callback=progress.denoise @ (0, 0.25),
            )
            if not ok:
                raise RuntimeError("Denoising vocals with ffmpeg failed.")
            # ~75% of denoise step is silence detection and muting
            silence.mute_non_singing_parts(
                paths.vocals_denoised,
                paths.vocals_muted,
                progress_callback=progress.denoise @ (0.25, 1.0),
            )
            __print_time(perf_counter() - t)
        else:
            __print_cached(paths.vocals_denoised)
        progress.denoise(True)

        # transcribe audio
        __print_step(f"Transcribing audio using whisperx ({cfg.whisper_model})")
        t = perf_counter()
        if should_run(paths.transcription, ctx.force, Force.TRANSCRIBE):
            language, transcribed_data = whisper.transcribe(
                audio_path=paths.vocals_muted,
                lyrics_path=None if cfg.no_lyrics else paths.lyrics,
                model_arch=str(cfg.whisper_model),
                progress_callback=progress.transcription,
            )
            if len(transcribed_data) == 0:
                raise RuntimeError("Transcription failed.")
            models.to_json(transcribed_data, paths.transcription)
            paths.language.write_text(language)
            __print_time(perf_counter() - t)
        else:
            transcribed_data = models.from_json(
                list[TranscribedData], paths.transcription
            )
            language = paths.language.read_text().strip()
            __print_cached(paths.language)
            __print_cached(paths.transcription)
        progress.transcription(True)

        # detect musical properties
        __print_step("Detecting pitch using swift-f0")
        t = perf_counter()
        bpm = usdx.detect_bpm(paths.audio)
        print(f"BPM: {bpm:.1f}")
        progress.pitch(0.3)  # just rough estimates
        detected_key, detected_mode = usdx.detect_key(paths.audio)
        allowed_notes_for_key = usdx.get_allowed_notes_for_key(
            detected_key, detected_mode
        )
        print(f"Key: {detected_key} {detected_mode}")
        progress.pitch(0.4)
        if should_run(paths.pitch, ctx.force, Force.PITCH):
            # NOTE: can't track exact progress with onnxruntime
            pitched_data = swift_f0.detect_pitch(paths.vocals_muted)
            models.to_json(pitched_data, paths.pitch)
            __print_time(perf_counter() - t)
        else:
            pitched_data = models.from_json(PitchedData, paths.pitch)
            __print_cached(paths.pitch)
        progress.pitch(True)

        # generate TXT in UltraStar format
        __print_step("Generating UltraStar TXT file")
        t = perf_counter()
        if should_run(paths.song_gen_txt, ctx.force, Force.TXT):
            # hyphens.remove_punctuation_(transcribed_data, '.,"')
            transcribed_data = hyphens.hyphenate_transcription(
                transcribed_data, language
            )
            progress.generate_txt(0.1)  # just rough estimates
            transcribed_data = silence.remove_from_transcription(
                paths.vocals, transcribed_data
            )
            progress.generate_txt(0.5)
            transcribed_data = syllables.split_into_segments(transcribed_data, bpm)
            midi_segments = usdx.create_midi_segments(
                transcribed_data, pitched_data, allowed_notes_for_key
            )
            progress.generate_txt(0.95)
            midi_segments, transcribed_data = syllables.merge_segments(
                midi_segments, transcribed_data, bpm
            )
            if not cfg.no_lyrics and paths.lyrics.exists():
                phrase_splits = [t for t, _ in lyrics.parse(paths.lyrics.read_text())]
            else:
                phrase_splits = None
            progress.generate_txt(0.97)
            notes, bpm, gap = usdx.midi_to_ultrastar_txt(
                midi_segments, bpm, phrase_splits, ctx.phrase_correction
            )
            progress.generate_txt(0.99)
            txt = usdx_format.create(
                notes=notes,
                song_meta=song_meta,
                bpm=bpm,
                gap=gap,
                audio_path=paths.audio,
                cover_path=paths.cover,
                vocals_path=paths.vocals,
                instrumental_path=paths.instrumental,
            )
            __print_time(perf_counter() - t)
            paths.song_gen_txt.write_text(txt)
        else:
            txt = paths.song_gen_txt.read_text()
            __print_cached(paths.song_gen_txt)
        progress.generate_txt(True)

    __print_step("Producing final TXT file")
    t = perf_counter()
    if paths.cover.exists():
        txt = usdx_format.update_metadata(txt, {"COVER": paths.cover.name})
    if paths.bg.exists():
        txt = usdx_format.update_metadata(txt, {"BACKGROUND": paths.bg.name})
    if paths.video.exists():
        txt = usdx_format.update_metadata(txt, {"VIDEO": paths.video.name})
    txt = usdx_format.update_metadata(
        txt,
        {
            "MP3": paths.audio.name,
            "AUDIO": paths.audio.name,
            "VOCALS": paths.vocals.name,
            "INSTRUMENTAL": paths.instrumental.name,
        },
    )
    paths.song_txt.write_text(txt, "utf-8")

    # print final result
    __print_step("Done")
    stats: list[tuple[str, str]] = []
    for p in sorted(paths.base_dir.glob("*")):
        if p.is_file():
            stats.append((str(p), fmt.bytes(p.stat().st_size)))
    c1 = max(len(p) for p, _ in stats) + 4
    c2 = max(len(s) for _, s in stats)
    for s1, s2 in stats:
        print(f"{s1:{c1}s}{s2:>{c2}s}")
    dir_size = sum(f.stat().st_size for f in paths.base_dir.glob("**/*") if f.is_file())
    print("-" * (c1 + c2))
    print(f"{ansi.BOLD}Total: {fmt.bytes(dir_size):>{c1 + c2 - 7}s}{ansi.RESET}")
    progress.finish()


def __print_step(step: str) -> None:
    """Print pipeline step header."""
    print(f"{ansi.CYAN}{ansi.BOLD}[ {step} ]{ansi.RESET}", flush=True)


def __print_time(elapsed: float) -> None:
    """Print step timing."""
    print(f"{ansi.DIM}~~> Took {fmt.time(elapsed)}{ansi.RESET}", flush=True)


def __print_cached(file: Path | str) -> None:
    """Print in case of reusing a cached result."""
    print(f"{ansi.DIM}~~> Using cached result: {file}{ansi.RESET}", flush=True)
