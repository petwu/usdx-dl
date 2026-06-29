"""Models shared by other modules."""

import json
import re
import shutil
from enum import StrEnum
from pathlib import Path
from typing import Self, Sequence, TypeVar

from pydantic import AliasGenerator, BaseModel, ConfigDict, TypeAdapter

from usdx_dl import __app__


def snake_to_camel_case(snake_str: str) -> str:
    """Convert a snake_case string to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


config = ConfigDict(
    alias_generator=AliasGenerator(
        validation_alias=snake_to_camel_case,
        serialization_alias=snake_to_camel_case,
    ),
    validate_by_name=True,
    validate_by_alias=True,
)


def to_json(
    obj: BaseModel | Sequence[BaseModel],
    path: Path | str | None = None,
    indent: int = 2,
    **kwargs,
) -> str:
    """Serialize and save as JSON."""
    if isinstance(obj, BaseModel):
        s = obj.model_dump_json(indent=indent, **kwargs)
    else:
        s = json.dumps(
            [item.model_dump(mode="json") for item in obj],
            indent=indent,
            **kwargs,
        )
    if path:
        Path(path).write_text(s, encoding="utf-8")
    return s


T = TypeVar("T", bound=BaseModel | Sequence[BaseModel])


def from_json(
    cls: type[T],
    path_or_str: Path | str,
    strict: bool | None = None,
    by_name: bool = True,
    **kwargs,
) -> T:
    """Deserialize from JSON."""
    if isinstance(path_or_str, str) and not Path(path_or_str).exists():
        s = path_or_str
    else:
        s = Path(path_or_str).read_text(encoding="utf-8")
    return TypeAdapter(cls).validate_json(
        s,
        strict=strict,
        by_name=by_name,
        **kwargs,
    )


class Config(BaseModel):
    """App config."""

    usdb_cookie: str | None = None
    download_tools: bool = False

    model_config = config

    @classmethod
    def path(cls) -> Path:
        """Path to the config file."""
        return __app__.user_config_path / "config.json"

    def save(self) -> None:
        """Save the server state to disk."""
        path = Config.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2, by_alias=False), "utf-8")

    @classmethod
    def load(cls) -> Self:
        """Load the server state from disk."""
        path = Config.path()
        if not path.exists():
            return cls()
        return cls.model_validate_json(path.read_text("utf-8"), by_name=True)


class Tool(BaseModel):
    """Model representing a missing required tool."""

    name: str
    path: Path
    version: str | None
    latest: str
    download_url: str
    homepage: str

    model_config = config


class SongMetadata(BaseModel):
    """Metadata related to a song."""

    artist: str
    title: str
    year: int
    genre: str | None = None
    language: str | None = None
    usdb_url: str | None = None
    video_url: str | None = None
    cover_url: str | None = None
    bg_url: str | None = None

    model_config = config

    def __repr__(self) -> str:
        return (
            f"{self.artist} - {self.title} ["
            + ", ".join(str(x) for x in [self.year, self.language, self.genre] if x)
            + "]"
            + (f" ({self.video_url})" if self.video_url else "")
        )

    def __str__(self) -> str:
        return repr(self)

    def merge_(self, other: Self | None, *, override: bool = False) -> Self:
        """Merge unset attributes with another instance inplace.
        If override is True, also override set attributes."""
        if other is None:
            return self
        for name, field in SongMetadata.model_fields.items():
            val_self = getattr(self, name, None)
            val_other = getattr(other, name, None)
            if override or (val_self == field.default and val_other != field.default):
                setattr(self, name, val_other)
        return self


class SongPaths:
    """Paths to all relevant files for a song."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.tmp_dir = output_dir / "tmp"
        self.song_orig_txt = self.tmp_dir / "song.usdb"
        self.song_gen_txt = self.tmp_dir / "song.gen"
        self.song_txt = output_dir / "song.txt"
        self.meta = output_dir / "metadata.json"
        self.lyrics = self.tmp_dir / "lyrics.txt"
        self.cover = output_dir / "cover.jpg"
        self.bg = output_dir / "background.jpg"
        self.video = output_dir / "video.mp4"
        self.audio = output_dir / "audio.mp3"
        self.language = self.tmp_dir / "language.txt"
        self.transcription = self.tmp_dir / "transcription.json"
        self.pitch = self.tmp_dir / "pitch.json"
        self.vocals = output_dir / "vocals.mp3"
        self.vocals_denoised = self.tmp_dir / "vocals_denoised.mp3"
        self.vocals_muted = self.tmp_dir / "vocals_muted.mp3"
        self.instrumental = output_dir / "instrumental.mp3"

    def mkdirs(self):
        """Create all necessary directories."""
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean(self):
        """Remove all files in the output directory."""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def name_path(self, artist: str, title: str) -> Path:
        """Get the path to the file that contains the song name."""
        return self.output_dir / re.sub(
            r"[^a-zA-Z0-9 _\-.,@()\[\]]",
            "",
            f"@ {artist} - {title}",
        )

    def is_complete(self) -> bool:
        """Check if all necessary files are present."""
        return (
            self.song_txt.exists()
            and self.audio.exists()
            and self.cover.exists()
            and self.meta.exists()
        )


class Force(StrEnum):
    """Argument value for ``--force``."""

    CLEAN = "clean"
    ALL = "all"
    DOWNLOAD = "download"
    SPLIT_STEMS = "split-stems"
    TRANSCRIBE = "transcribe"
    DENOISE = "denoise"
    PITCH = "pitch"
    TXT = "txt"


class PipelineContext(BaseModel):
    """Context object to hold all relevant data and paths during pipeline execution."""

    uuid: str
    url_or_id: str
    usdb_cookie: str | None = None
    output_dir: Path
    models_dir: Path
    stem_model: str
    whisper_model: str
    sample_rate: int = 44100
    vocals_gain: float = 0.0
    phrase_correction: float = 1.0
    force: Force | None = None
    no_lyrics: bool = False
    no_video: bool = False
    non_interactive: bool = False
    lyrics: str | None = None
    meta: SongMetadata | None = None
    reviewed: bool | None = None
    errors: list[str] | None = None

    model_config = config


class TranscribedData(BaseModel):
    """Result item from transcription."""

    word: str
    start: float
    end: float
    score: float = 0.0
    is_hyphen: bool = False
    is_word_end: bool = True


class PitchedData(BaseModel):
    """Pitched data from crepe"""

    times: list[float]
    frequencies: list[float]
    confidence: list[float]


class MidiSegment(BaseModel):
    """Note-word segment."""

    note: str
    start: float
    end: float
    word: str
