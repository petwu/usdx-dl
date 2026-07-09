"""Client for https://lrclib.net."""

import re
from typing import Final

import requests

__all__ = ["search", "URL"]


URL: Final[str] = "https://lrclib.net"


def search(
    artist: str,
    title: str,
    synced: bool = True,
    timeout: int = 30,
) -> str | None:
    """Search for lyrics.

    Args:
        artist: Artist name.
        title: Song title.
        synced: Whether to return the synced lyrics with timestamps.
        timeout: Request timeout in seconds.

    Returns:
        Multi-line lyrics string for the first search result.
        None if the request failed or no lyrics were found.
    """
    params = {"q": f"{artist} {title}"}
    headers = {"Accept": "application/json"}
    with requests.get(
        f"{URL}/api/search",
        params=params,
        headers=headers,
        timeout=timeout,
    ) as response:
        if not response.ok:
            return None
        data: list[dict] = response.json()
    if len(data) == 0:
        return None
    return data[0]["syncedLyrics" if synced else "plainLyrics"]


def parse(lyrics: str) -> list[tuple[float, str]]:
    """Parse synced lyrics in `LRC <https://en.wikipedia.org/wiki/LRC_(file_format)>`_
    format into (timestamp, text) tuples."""
    parsed: list[tuple[float, str]] = []
    for line in lyrics.splitlines():
        line = line.strip()
        # skip blank lines, comments and metadata/ID tags
        if not line or line.startswith("#") or re.match(r"^\[[a-z]+:.+\]$", line):
            continue
        match = re.match(
            r"\[(?P<minute>\d+):(?P<second>\d+(\.\d+)?)\](?P<text>.*)",
            line,
        )
        if not match:
            raise ValueError(f"Invalid lyrics format. Failed to parse line: '{line}'")
        timestamp = int(match.group("minute")) * 60 + float(match.group("second"))
        text = match.group("text").strip()
        parsed.append((timestamp, text))
    return parsed


def strip(lyrics: str) -> str:
    """Remove LRC metadata and timestamps from synced lyrics."""
    stripped: list[str] = []
    for line in lyrics.splitlines():
        line = line.strip()
        # skip comments and metadata/ID tags
        if line.startswith("#") or re.match(r"^\[[a-z]+:.+\]$", line):
            continue
        # remove timestamps
        line = re.sub(r"\[\d+:\d+(\.\d+)?\]", "", line).strip()
        stripped.append(line)
    return "\n".join(stripped)
