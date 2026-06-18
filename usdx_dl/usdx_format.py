"""Helpers to parse and manipulate TXT files according to the UltraStar Format.

See:
    https://usdx.eu/format
"""

from pathlib import Path

from usdx_dl.models import SongMetadata


def parse_metadata(txt: str) -> SongMetadata | None:
    """Parse song metadata from a UltraStar TXT file."""

    def get(key: str) -> str:
        for line in txt.splitlines():
            line = line.strip()
            if not line.startswith("#"):
                break  # end of header
            if line.startswith(f"#{key}:"):
                return line[len(f"#{key}:") :].strip()
        return ""

    return SongMetadata(
        artist=get("ARTIST"),
        title=get("TITLE"),
        year=int(get("YEAR")),
        genre=get("GENRE"),
        language=get("LANGUAGE"),
    )


def update_metadata(txt: str, kv: dict[str, str | None]) -> str:
    """Set or unset a specific metadata field."""
    lines = txt.splitlines()

    for key, value in kv.items():
        for i, line in enumerate(lines):
            line = line.strip()
            if not line.startswith("#"):
                if value:
                    lines.insert(i, f"#{key}:{value}")
                break  # end of header
            if line.startswith(f"#{key}:"):
                if value:
                    lines[i] = f"#{key}:{value}"
                else:
                    del lines[i]
                break

    return "\n".join(lines)


def create(
    notes: list[str],
    song_meta: SongMetadata,
    bpm: int | float,
    gap: int | float,
    audio_path: Path,
    cover_path: Path | None = None,
    vocals_path: Path | None = None,
    instrumental_path: Path | None = None,
) -> str:
    """Assemble a valid TXT file with the provided arguments."""
    txt = ""
    # metadata
    txt += "#VERSION:1.2.0\n"
    txt += "#CREATOR:petwu\n"
    txt += f"#ARTIST:{song_meta.artist}\n"
    txt += f"#TITLE:{song_meta.title}\n"
    txt += f"#YEAR:{song_meta.year}\n"
    if song_meta.genre:
        txt += f"#GENRE:{song_meta.genre}\n"
    if song_meta.language:
        txt += f"#LANGUAGE:{song_meta.language}\n"
    txt += f"#BPM:{round(bpm, 2)}\n"
    txt += f"#GAP:{int(round(gap * 1000))}\n"
    txt += f"#MP3:{audio_path.name}\n"
    if cover_path:
        txt += f"#COVER:{cover_path.name}\n"
    txt += f"#AUDIO:{audio_path.name}\n"
    if vocals_path:
        txt += f"#VOCALS:{vocals_path.name}\n"
    if instrumental_path:
        txt += f"#INSTRUMENTAL:{instrumental_path.name}\n"
    # notes
    txt += "\n".join(notes)
    return txt
