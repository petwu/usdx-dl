"""YouTube client."""

import json
import re
import subprocess
from pathlib import Path

from usdx_dl import fmt
from usdx_dl.models import SongMetadata

__all__ = ["APIClient", "search"]


class APIClient:
    """Client to interact with a specific YouTube video."""

    def __init__(self, url_or_id: str) -> None:
        """
        Args:
            url_or_id: YouTube video URL or ID.
        """
        if url_or_id.startswith("http"):
            match = re.search(r"watch\?v=([\w_-]+)", url_or_id)
            if not match:
                raise ValueError(f"Invalid URL (missing `v=id`): {url_or_id}")
            self.id = match.group(1)
        else:
            self.id = url_or_id
        self.url = f"https://www.youtube.com/watch?v={self.id}"
        self._data: dict | None = None

    @property
    def data(self) -> dict:
        """Video metadata."""
        if self._data is None:
            args = ["yt-dlp", "--dump-json", self.id]
            output = subprocess.run(args, stdout=subprocess.PIPE, check=True).stdout
            self._data = json.loads(output.decode("utf-8"))
        return self._data  # type: ignore

    @data.setter
    def data(self, value: dict) -> None:
        self._data = value

    def get_metadata(self) -> SongMetadata:
        """Determine song metadata from the video information."""
        artist = (
            self.data.get("artist")
            or self.data.get("creator")
            or self.data.get("channel", "Unknown")
        )
        title = fmt.clean_title(self.data["title"], artist)
        year = int(self.data.get("release_year") or self.data["upload_date"][:4])
        thumbnail = self.data.get("thumbnail")
        return SongMetadata(
            artist=artist,
            title=title,
            year=year,
            video_url=self.url,
            cover_url=thumbnail,
            bg_url=thumbnail,
        )

    def download_audio(self, path: Path | str, sample_rate: int) -> bool:
        """Download the audio of the video."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        args = [
            "yt-dlp",
            "-f",
            "bestaudio",
            "--extract-audio",
            "--audio-format",
            path.suffix[1:],
            "--postprocessor-args",
            f"ffmpeg:-ar {sample_rate}",
            "--force-overwrites",
            "-o",
            path.as_posix(),
            f"https://www.youtube.com/watch?v={self.id}",
        ]
        return subprocess.run(args, check=False).returncode == 0

    def download_video(self, path: Path | str) -> bool:
        """Download the video."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        args = [
            "yt-dlp",
            "-f",
            f"bestvideo[ext={path.suffix[1:]}][height<=1080]",
            "--force-overwrites",
            "-o",
            path.as_posix(),
            f"https://www.youtube.com/watch?v={self.id}",
        ]
        return subprocess.run(args, check=False).returncode == 0


def search(query: str) -> APIClient:
    """Search for a song/video and return a client instance for the first match."""
    args = [
        "yt-dlp",
        "--match-filters",
        "original_url!*=/shorts/",
        "--flat-playlist",
        "--dump-json",
        f"ytsearch1:{query}",
    ]
    output = subprocess.run(args, stdout=subprocess.PIPE, check=True).stdout
    data = json.loads(output.decode("utf-8"))
    obj = APIClient(data["id"])
    obj.data = data
    return obj
