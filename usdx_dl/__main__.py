"""Download all necessary files (txt, cover, audio, video, etc.) for UltraStar Deluxe
and similar games that support UltraStar .txt files.

Uses AI models for these tasks:
- separation of vocals and instrumental stems (demucs or Mel-Band RoFormer)
- audio description (whisperx) [not for USDB links]
- pitch detection (swift-f0) [not for USDB links]

Getting started:
1.  Go to https://usdb.animux.de, create an account and search for songs.
2a. Copy the song URL and run:
    $ usdx-dl "https://usdb.animux.de/?link=detail&id=1368"
2b. If you can't find the song on USDB, you can also provide a YouTube link:
    $ usdx-dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    Note: This generates the TXT file using AI models for lyric transcription
    and pitch detection and will be less accurate.
"""

import argparse
import io
import json
import logging
import os
import re
import sys
from dataclasses import asdict
from enum import StrEnum
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
    config,
    ffmpeg,
    fmt,
    hyphens,
    lyrics,
    silence,
    syllables,
    usdb,
    usdx,
    usdx_format,
    whisper,
    youtube,
)
from usdx_dl.models import PitchedData, SongMetadata, TranscribedData


class Force(StrEnum):
    """Argument value for ``--force``."""

    ALL = "all"
    DOWNLOAD = "download"
    SPLIT_STEMS = "split-stems"
    TRANSCRIBE = "transcribe"
    DENOISE = "denoise"
    PITCH = "pitch"
    TXT = "txt"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "url_or_id",
        type=str,
        help="Song URL or ID from https://usdb.animux.de or https://www.youtube.com.",
    )
    parser.add_argument(
        "-c",
        "--usdb-cookie",
        metavar="PHPSESSID",
        type=str,
        help="USDB login session cookie for API requests.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        type=Path,
        default="songs",
        help="Output directory. (default: %(default)s)",
    )
    parser.add_argument(
        "-m",
        "--models-dir",
        type=Path,
        default=Path(__file__).parent.parent / ".models",
        help="Model cache directory. (default: %(default)s)",
    )
    parser.add_argument(
        "-s",
        "--stem-model",
        type=str,
        choices=["demucs", "mel-roformer"],
        default="demucs",
        help="Model used for stem separation. (default: %(default)s)",
    )
    parser.add_argument(
        "-w",
        "--whisper-model",
        type=str,
        default="turbo",
        choices=["tiny", "base", "small", "medium", "large", "turbo"],
        help="Model size of the WhisperX model used for transcription. "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "-r",
        "--sample-rate",
        metavar="INT",
        type=int,
        default=44100,
        help="Audio sample rate. (default: %(default)s)",
    )
    parser.add_argument(
        "-g",
        "--vocals-gain",
        type=float,
        metavar="0..1",
        default=0.0,
        help="Gain in [0, 1] for the vocals. Higher means vocals are louder. "
        "Use only if you use another game than UltraStart Deluxe that doesn't "
        "support setting the vocals volume within the game. "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "-p",
        "--phrase-correction",
        metavar="FLOAT",
        type=float,
        default=1.0,
        help="Manually correct for unintuitive phrase splits. If phrases are too "
        "short use a value >1, for too long phases a value in [0, 1). "
        "Use with `-f txt` to try various values. "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "-f",
        "--force",
        type=str,
        nargs="?",
        const="all",
        choices=list(Force),
        help="Force to rerun everything or just a specific step. "
        "Defaults to 'all' without argument.",
    )
    parser.add_argument(
        "-v",
        "--no-video",
        action="store_true",
        help="Don't download the music video from YouTube and set a static "
        "background image instead.",
    )
    parser.add_argument(
        "-l",
        "--no-lyrics",
        action="store_true",
        help="Don't search for synced lyrics on https://lrclib.net, instead "
        "always transcribe with WhisperX.",
    )
    parser.add_argument(
        "-n",
        "--non-interactive",
        action="store_true",
        help="Enable non-interactive mode.",
    )
    return parser.parse_args()


def run_pipeline(
    url_or_id: str,
    usdb_cookie: str,
    output_dir: Path,
    models_dir: Path,
    stem_model: str,
    whisper_model: str,
    sample_rate: int,
    vocals_gain: float,
    phrase_correction: float,
    force: Force,
    no_lyrics: bool,
    no_video: bool,
    non_interactive: bool,
) -> None:
    """Args: See :func:`parse_args`."""
    os.environ["TORCH_HOME"] = str(models_dir / "torch")
    os.environ["HF_HOME"] = str(models_dir / "hf")

    # detect if we start from USDB or YouTube
    if "usdb.animux.de" in url_or_id or url_or_id.isdigit():
        if not usdb_cookie:
            usdb_cookie = config.get("usdb_cookie")
            if not usdb_cookie:
                if non_interactive:
                    raise RuntimeError("Cannot continue without --usdb-cookie.")
                usdb_cookie = input(f"PHPSESSID cookie from {usdb.APIClient.URL}: ")
                if len(usdb_cookie.replace("PHPSESSID=", "")) < 22:
                    raise ValueError(
                        "Invalid PHPSESSID, must be at least 22 characters."
                    )
        config.set("usdb_cookie", usdb_cookie)
        usdb_client = usdb.APIClient(url_or_id, usdb_cookie)
        yt_client = None
        song_id = str(usdb_client.id)
    elif "youtube.com" in url_or_id or re.match(r"^[\w_-]{11}$", url_or_id):
        usdb_client = None
        yt_client = youtube.APIClient(url_or_id)
        song_id = yt_client.id
    else:
        raise ValueError(f"Invalid URL or ID: {url_or_id}")

    # output paths
    output_dir /= str(song_id)
    tmp_dir = output_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    song_orig_txt_path = tmp_dir / "song.usdb"
    song_gen_txt_path = tmp_dir / "song.gen"
    song_txt_path = output_dir / "song.txt"
    meta_path = output_dir / "metadata.json"
    lyrics_path = tmp_dir / "lyrics.txt"
    cover_path = output_dir / "cover.jpg"
    bg_path = output_dir / "background.jpg"
    video_path = output_dir / "video.mp4"
    audio_path = output_dir / "audio.mp3"
    language_path = tmp_dir / "language.txt"
    transcription_path = tmp_dir / "transcription.json"
    pitch_path = tmp_dir / "pitch.json"
    vocals_path = output_dir / "vocals.mp3"
    vocals_denoised_path = tmp_dir / "vocals_denoised.mp3"
    vocals_muted_path = tmp_dir / "vocals_muted.mp3"
    instrumental_path = output_dir / "instrumental.mp3"

    if usdb_client is not None:
        print_step("Downloading TXT from USDB")
        # download lyrics/txt file from USDB
        if should_run(song_orig_txt_path, force, Force.DOWNLOAD):
            txt = usdb_client.fetch_txt()
            if txt is None:
                config.unset("usdb_cookie")
                raise RuntimeError(f"Failed to fetch TXT for {url_or_id}")
            song_orig_txt_path.write_text(txt, "utf-8")
            print_time()
        else:
            txt = song_orig_txt_path.read_text("utf-8")
            print_cached(song_orig_txt_path)

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

    else:
        assert yt_client is not None
        song_meta = None
        txt = None

    print_step("Collecting song metadata")
    if should_run(meta_path, force, Force.DOWNLOAD):
        yt_meta = yt_client.get_metadata()
        if song_meta is None:
            song_meta = yt_meta
        else:
            song_meta.merge_(yt_meta)
        if not non_interactive:
            print("Please check the following metadata")
            song_meta.artist = (
                input(f"- Artist [{song_meta.artist}]: ") or song_meta.artist
            )
            song_meta.title = input(f"- Title [{song_meta.title}]: ") or song_meta.title
        song_meta.serialize(meta_path)
        print_time()
    else:
        song_meta = SongMetadata.load(meta_path)
        print_cached(meta_path)
    print(song_meta)

    # download cover image
    print_step("Downloading cover and background image")
    if song_meta.cover_url and should_run(cover_path, force, Force.DOWNLOAD):
        with requests.get(song_meta.cover_url, timeout=30) as response:
            response.raise_for_status()
            cover = Image.open(io.BytesIO(response.content))
        crop_size = min(cover.width, cover.height)
        left = (cover.width - crop_size) // 2
        top = (cover.height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size
        with open(cover_path, "wb") as f:
            cover.crop((left, top, right, bottom)).save(f)
        if not song_meta.bg_url:
            print_time()
    elif song_meta.cover_url:
        print_cached(cover_path)
    else:
        print("No cover found.")
    if song_meta.bg_url and should_run(bg_path, force, Force.DOWNLOAD):
        with requests.get(song_meta.bg_url, timeout=30) as response:
            response.raise_for_status()
            background = Image.open(io.BytesIO(response.content))
        with open(bg_path, "wb") as f:
            background.save(f)
        print_time()
    else:
        print_cached(bg_path)

    # download audio/video from YouTube
    if yt_client is None:
        raise RuntimeError(f"Failed to find YouTube for {url_or_id}.")
    if no_video:
        print_step("Downloading audio from YouTube")
    else:
        print_step("Downloading video and audio from YouTube")
        if should_run(video_path, force, Force.DOWNLOAD):
            ok = yt_client.download_video(video_path)
            if not ok:
                raise RuntimeError(f"Failed to download YouTube video: {yt_client.url}")
        else:
            print_cached(video_path)
    if should_run(audio_path, force, Force.DOWNLOAD):
        ok = yt_client.download_audio(audio_path, sample_rate)
        if not ok:
            raise RuntimeError(f"Failed to download YouTube video: {yt_client.url}")
        print_time()
    else:
        print_cached(audio_path)

    # split vocals using AI model
    print_step(f"Splitting vocals and instrumental parts using {stem_model}")
    if should_run(vocals_path, force, Force.SPLIT_STEMS):
        separator = Separator(
            log_level=logging.INFO,
            model_file_dir=(models_dir / "separator").as_posix(),
            output_dir=output_dir.as_posix(),
            output_format=vocals_path.suffix[1:],
            sample_rate=sf.info(audio_path).samplerate,
        )
        model_name_mapping = {
            # cSpell: disable
            "demucs": "htdemucs.yaml",
            "mel-roformer": "mel_band_roformer_karaoke_becruily.ckpt",
            # cSpell: enable
        }
        separator.load_model(model_name_mapping[stem_model])
        output_names = {
            "Vocals": "vocals",
            "Instrumental": "instrumental",
            "Drums": "drums",
            "Bass": "bass",
            "Other": "other",
        }
        separator.separate(audio_path.as_posix(), output_names)
        if stem_model in ["demucs"]:
            stem_names = {
                "demucs": ["drums", "bass", "other"],
            }[stem_model]
            stem_paths = [
                output_dir / f"{stem}.{vocals_path.suffix[1:]}" for stem in stem_names
            ]
            stems = [sf.read(p) for p in stem_paths]
            assert all(sr == sample_rate for _, sr in stems), (
                f"Sample rates don't match: {[sr for _, sr in stems]}"
            )
            instrumental = sum(data for data, _ in stems)
            instrumental = np.clip(instrumental, -1.0, 1.0)
            sf.write(instrumental_path, instrumental, sample_rate)  # type: ignore
            for p in stem_paths:
                p.unlink()

        print_time()
    else:
        print_cached(vocals_path)
        print_cached(instrumental_path)

    if vocals_gain > 0:
        vocals, _ = sf.read(vocals_path)
        instrumental, _ = sf.read(instrumental_path)
        instrumental_plus_vocals = instrumental + vocals_gain * vocals
        instrumental_path = instrumental_path.with_stem(
            instrumental_path.stem + f"_{vocals_gain}x_vocals"
        )
        sf.write(instrumental_path, instrumental_plus_vocals, sample_rate)

    if txt is None:
        # find lyrics
        if not no_lyrics:
            print_step("Downloading lyrics")
            if should_run(lyrics_path, force, Force.DOWNLOAD):
                lyrics_sync = lyrics.search(
                    song_meta.artist, song_meta.title, synced=True
                )
                if lyrics_sync is None:
                    print("No lyrics found.")
                    if not non_interactive:
                        google_url = "https://www.google.com/search?q=" + quote_plus(
                            f'{song_meta.artist} {song_meta.title} lyrics "lrc"'
                        )
                        print(f"Search for them on Google: {google_url}")
                        print(
                            "Then paste the synched lyrics (LRC format) here [empty to skip]:"
                        )
                        lines: list[str] = []
                        while True:
                            line = input().strip()
                            if line == "" and len(lines) > 0 and lines[-1] == "":
                                break
                            lines.append(line)
                        if len(lines) >= 10:
                            lyrics_sync = "\n".join(lines).strip()
                            lyrics_path.write_text(lyrics_sync)
                        else:
                            print("- skip -")
                else:
                    print(lyrics_sync)
                    ok = non_interactive or input(
                        "Lyrics correct? ([y]/n): "
                    ).lower().strip() in ("y", "yes", "")
                    if ok:
                        lyrics_path.write_text(lyrics_sync)
                    else:
                        lyrics_sync = None
                print_time()
            else:
                lyrics_sync = lyrics_path.read_text()
                print_cached(lyrics_path)

        # preprocess vocals audio
        print_step("Denoising vocals stem")
        if should_run(vocals_denoised_path, force, Force.DENOISE) or should_run(
            vocals_muted_path, force, Force.DENOISE
        ):
            ok = ffmpeg.denoise_vocal_audio(
                vocals_path, vocals_denoised_path, mono=True
            )
            if not ok:
                raise RuntimeError("Denoising vocals with ffmpeg failed.")
            silence.mute_non_singing_parts(vocals_denoised_path, vocals_muted_path)
            print_time()
        else:
            print_cached(vocals_denoised_path)

        # transcribe audio
        print_step(f"Transcribing audio using whisperx ({whisper_model})")
        if should_run(transcription_path, force, Force.TRANSCRIBE):
            language, transcribed_data = whisper.transcribe(
                audio_path=vocals_muted_path,
                lyrics_path=None if no_lyrics else lyrics_path,
                model_arch=whisper_model,
            )
            if len(transcribed_data) == 0:
                raise RuntimeError("Transcription failed.")
            transcription_path.write_text(
                json.dumps([asdict(i) for i in transcribed_data], indent=2)
            )
            language_path.write_text(language)
            print_time()
        else:
            transcribed_data = [
                TranscribedData(**i) for i in json.loads(transcription_path.read_text())
            ]
            language = language_path.read_text().strip()
            print_cached(language_path)
            print_cached(transcription_path)

        # detect musical properties
        print_step("Detecting pitch using swift-f0")
        bpm = usdx.detect_bpm(audio_path)
        print(f"BPM: {bpm:.1f}")
        detected_key, detected_mode = usdx.detect_key(audio_path)
        allowed_notes_for_key = usdx.get_allowed_notes_for_key(
            detected_key, detected_mode
        )
        print(f"Key: {detected_key} {detected_mode}")
        if should_run(pitch_path, force, Force.PITCH):
            pitched_data = usdx.detect_pitch(vocals_muted_path)
            pitched_data.serialize(pitch_path)
            print_time()
        else:
            pitched_data = PitchedData.load(pitch_path)
            print_cached(pitch_path)

        # generate TXT in UltraStar format
        print_step("Generating UltraStar TXT file")
        if should_run(song_gen_txt_path, force, Force.TXT):
            # hyphens.remove_punctuation_(transcribed_data, '.,"')
            transcribed_data = hyphens.hyphenate_transcription(
                transcribed_data, language
            )
            transcribed_data = silence.remove_from_transcription(
                vocals_path, transcribed_data
            )
            transcribed_data = syllables.split_into_segments(transcribed_data, bpm)
            midi_segments = usdx.create_midi_segments(
                transcribed_data, pitched_data, allowed_notes_for_key
            )
            midi_segments, transcribed_data = syllables.merge_segments(
                midi_segments, transcribed_data, bpm
            )
            if not no_lyrics and lyrics_path.exists():
                phrase_splits = [t for t, _ in lyrics.parse(lyrics_path.read_text())]
            else:
                phrase_splits = None
            notes, bpm, gap = usdx.midi_to_ultrastar_txt(
                midi_segments, bpm, phrase_splits, phrase_correction
            )
            txt = usdx_format.create(
                notes=notes,
                song_meta=song_meta,
                bpm=bpm,
                gap=gap,
                audio_path=audio_path,
                cover_path=cover_path,
                vocals_path=vocals_path,
                instrumental_path=instrumental_path,
            )
            print_time()
            song_gen_txt_path.write_text(txt)
        else:
            txt = song_gen_txt_path.read_text()
            print_cached(song_gen_txt_path)

    print_step("Producing final TXT file")
    if cover_path.exists():
        txt = usdx_format.update_metadata(txt, {"COVER": cover_path.name})
    if bg_path.exists():
        txt = usdx_format.update_metadata(txt, {"BACKGROUND": bg_path.name})
    if video_path.exists():
        txt = usdx_format.update_metadata(txt, {"VIDEO": video_path.name})
    txt = usdx_format.update_metadata(
        txt,
        {
            "MP3": audio_path.name,
            "AUDIO": audio_path.name,
            "VOCALS": vocals_path.name,
            "INSTRUMENTAL": instrumental_path.name,
        },
    )
    song_txt_path.write_text(txt, "utf-8")

    # print final result
    print_step("Done")
    stats: list[tuple[str, str]] = []
    for p in sorted(output_dir.glob("*")):
        if p.is_file():
            stats.append((str(p), fmt.bytes(p.stat().st_size)))
    c1 = max(len(p) for p, _ in stats) + 4
    c2 = max(len(s) for _, s in stats)
    for s1, s2 in stats:
        print(f"{s1:{c1}s}{s2:>{c2}s}")
    output_dir_size = sum(
        f.stat().st_size for f in output_dir.glob("**/*") if f.is_file()
    )
    print("-" * (c1 + c2))
    print(f"{ansi.BOLD}Total: {fmt.bytes(output_dir_size):>{c1 + c2 - 7}s}{ansi.RESET}")


def should_run(output_file: Path | str, force_arg: Force, *force_types: Force) -> bool:
    """Helper to only run certain parts of the pipeline of either the output file
    doesn't exist or the ``--force`` flag is set."""
    return not Path(output_file).exists() or force_arg in ("all", *force_types)


__step_count: int = 0  # pylint: disable=invalid-name
__step_start: float


def print_step(step: str) -> None:
    """Print pipeline step header."""
    global __step_count, __step_start  # pylint: disable=global-statement
    __step_count += 1
    __step_start = perf_counter()
    print(f"{ansi.CYAN}{ansi.BOLD}[ {__step_count}. {step} ]{ansi.RESET}")


def print_time() -> None:
    """Print step timing."""
    elapsed = perf_counter() - __step_start
    time_str = ""
    if elapsed > 60:
        time_str += f"{int(elapsed // 60)}min "
    time_str += f"{elapsed % 60:.3f}s"
    print(f"{ansi.DIM}~~> Took {time_str}{ansi.RESET}")


def print_cached(file: Path | str) -> None:
    """Print in case of reusing a cached result."""
    print(f"{ansi.DIM}~~> Using cached result: {file}{ansi.RESET}")


def main():
    """Main function."""
    try:
        run_pipeline(**vars(parse_args()))
    except KeyboardInterrupt:
        print()
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"{ansi.RED}ERROR: {e.__class__.__name__}: {e}{ansi.RESET}", file=sys.stderr
        )
        raise e


if __name__ == "__main__":
    main()
