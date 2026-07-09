"""YouTube client."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import YoutubeDLError

from usdx_dl import ansi, fmt
from usdx_dl.ffmpeg import ProgressCallback
from usdx_dl.models import SongMetadata

__all__ = ["APIClient", "search"]


class APIClient:
    """Client to interact with a specific YouTube video."""

    def __init__(self, url_or_id: str, max_tries: int = 3) -> None:
        """
        Args:
            url_or_id: YouTube video URL or ID.
            max_tries: Maximum number of attempts in case of 403 Forbidden errors.
        """
        if url_or_id.startswith("http"):
            match = re.search(r"watch\?v=([\w_-]+)", url_or_id)
            if not match:
                raise ValueError(f"Invalid URL (missing `v=id`): {url_or_id}")
            self.id = match.group(1)
        else:
            self.id = url_or_id
        self.url = f"https://www.youtube.com/watch?v={self.id}"
        self.max_tries = max_tries
        self._data: dict | None = None

    @property
    def data(self) -> dict:
        """Video metadata."""
        if self._data is None:
            params: dict = {}
            with yt_dlp.YoutubeDL(params) as ydl:  # type: ignore
                self._data = dict(ydl.extract_info(self.url, download=False))
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
        duration = self.data.get("duration")
        thumbnail = self.data.get("thumbnail")
        return SongMetadata(
            artist=artist,
            title=title,
            year=year,
            duration=duration,
            video_url=self.url,
            cover_url=thumbnail,
            bg_url=thumbnail,
        )

    def describe(self) -> str:
        """Return a human-readable description of the video."""
        title = self.data["title"]
        uploader = self.data["uploader"]
        duration = fmt.time(self.data["duration"], decimals=0)
        return f"{title} by {uploader} @ {duration}"

    def is_youtube_url(self, url: str | None) -> bool:
        """Check if a URL is a YouTube URL."""
        if url is None:
            return False
        return (
            re.match(r"^https?://((www\.)?youtube\.com/|i\.ytimg.com/)", url)
            is not None
        )

    @staticmethod
    def progress_book(callback: ProgressCallback | None):
        """Create a progress hook for yt-dlp that calls the given callback with the
        download progress as a float in [0, 1]."""

        def hook(d: dict[str, Any]) -> None:
            if not callable(callback):
                return
            if d["status"] == "downloading":
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total_bytes:
                    progress = d["downloaded_bytes"] / total_bytes
                    progress = min(max(progress, 0.0), 1.0)
                    callback(progress)
            elif d["status"] == "finished":
                callback(1.0)

        return hook

    def download_audio(
        self,
        path: Path | str,
        sample_rate: int,
        progress_callback: ProgressCallback | None = None,
    ) -> bool:
        """Download the audio of the video."""
        attempt = 0
        while attempt < self.max_tries:
            attempt += 1
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            ext = path.suffix[1:] if path.suffix else "mp3"
            params = {
                # cSpell: disable
                "format": "bestaudio",  # -f bestaudio
                "final_ext": ext,  # --audio-format <ext>
                "outtmpl": {"default": path.as_posix()},  # -o <path>
                "overwrites": True,  # --force-overwrites
                "postprocessor_args": {
                    "ffmpeg": ["-ar", str(sample_rate)]
                },  # --postprocessor-args "ffmpeg:-ar <sample_rate>"
                "postprocessors": [  # --extract-audio
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": ext,
                    }
                ],
                # cSpell: enable
            }
            if ansi.color_enabled():
                params["color"] = {
                    "stderr": "always",
                    "stdout": "always",
                }  # --color always
            if callable(progress_callback):
                params["progress_hooks"] = [self.progress_book(progress_callback)]
            try:
                with yt_dlp.YoutubeDL(params) as ydl:  # type: ignore
                    ydl.download([self.url])
                return True
            except YoutubeDLError as e:
                print(f"Error occurred while downloading audio: {e}")
                print(f"Retrying audio download (attempt {attempt}/{self.max_tries}).")
        return False

    def download_video(
        self,
        path: Path | str,
        progress_callback: ProgressCallback | None = None,
    ) -> bool:
        """Download the video."""
        attempt = 0
        while attempt < self.max_tries:
            attempt += 1
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            ext = path.suffix[1:] if path.suffix else "mp4"
            params = {
                # cSpell: disable
                "format": f"bestvideo[ext={ext}][height<=1080]",  # -f bestvideo...
                "outtmpl": {"default": path.as_posix()},  # -o <path>
                "overwrites": True,  # --force-overwrites
                # cSpell: enable
            }
            if callable(progress_callback):
                params["progress_hooks"] = [self.progress_book(progress_callback)]
            try:
                with yt_dlp.YoutubeDL(params) as ydl:  # type: ignore
                    ydl.download([self.url])
                return True
            except YoutubeDLError as e:
                print(f"Error occurred while downloading video: {e}")
                print(f"Retrying video download (attempt {attempt}/{self.max_tries}).")
        return False


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
