"""Dataclasses shared by other modules."""

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from typing import Self


@dataclass
class SongMetadata:
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

    def __repr__(self) -> str:
        return (
            f"{self.artist} - {self.title} ["
            + ", ".join(str(x) for x in [self.year, self.language, self.genre] if x)
            + "]"
            + (f" ({self.video_url})" if self.video_url else "")
        )

    def merge_(self, other: Self) -> Self:
        """Merge unset attributes with another instance inplace."""
        for field in fields(self):
            val_self = getattr(self, field.name, None)
            val_other = getattr(other, field.name, None)
            if val_self == field.default and val_other != field.default:
                setattr(self, field.name, val_other)
        return self

    def serialize(self, path: Path | str) -> None:
        """Serialize and save as JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> Self:
        """Deserialize from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            return cls(**json.load(f))


@dataclass
class TranscribedData:
    """Result item from transcription."""

    word: str
    start: float
    end: float
    score: float = 0.0
    is_hyphen: bool = False
    is_word_end: bool = True


@dataclass
class PitchedData:
    """Pitched data from crepe"""

    times: list[float]
    frequencies: list[float]
    confidence: list[float]

    def serialize(self, path: Path | str) -> None:
        """Serialize and save as JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path | str) -> Self:
        """Deserialize from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            return cls(**json.load(f))


@dataclass
class MidiSegment:
    """Note-word segment."""

    note: str
    start: float
    end: float
    word: str
