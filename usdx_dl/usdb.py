"""UltraStar DataBase API client."""

import html
import re
from typing import Final

import requests


class APIClient:
    """Simple wrapper to query https://usdb.animux.de."""

    URL: Final[str] = "https://usdb.animux.de"

    def __init__(self, url_or_id: str | int, cookie: str) -> None:
        """
        Args:
            url_or_id: Song URL or ID.
            cookie: PHP session cookie extracted from a logged in session.
        """
        if isinstance(url_or_id, int) or url_or_id.isdigit():
            usdb_id = int(url_or_id)
        elif url_or_id.startswith("http"):
            match = re.search(r"[?&]id=(\d+)", url_or_id)
            if not match:
                raise ValueError(f"Invalid URL (missing `id`): {url_or_id}")
            usdb_id = int(match.group(1))
        else:
            usdb_id = int(url_or_id)

        cookie = cookie.strip("\"' ")
        if not cookie.startswith("PHPSESSID="):
            cookie = f"PHPSESSID={cookie}"

        self.id = usdb_id
        self.url = f"{self.URL}/?link=detail&id={self.id}"
        self.cookie = cookie

    def fetch_txt(self) -> str | None:
        """Download the TXT file."""
        with requests.post(
            f"{self.URL}/?link=gettxt&id={self.id}",
            headers={"Cookie": self.cookie},
            data={"wd": "1"},
            timeout=30,
        ) as response:
            page_html = response.content.decode("utf-8")
        if re.search(r"(please login|not logged in)", page_html, re.IGNORECASE):
            raise RuntimeError(
                f"Failed to fetch TXT file for {self.url}. "
                "The PHPSESSID cookie is invalid or expired."
            )
        # cSpell: disable-next-line
        if re.search(r"Datensatz nicht gefunden", page_html, re.IGNORECASE):
            raise RuntimeError(
                f"Failed to fetch TXT file for {self.url}. Song not found."
            )
        match = re.search(r"<textarea[^>]*>([\s\S]*)<\/textarea>", page_html)
        if not match:
            return None
        txt = match.group(1)
        txt = html.unescape(txt)  # replace &amp; and similar entities
        return txt

    def cover_url(self) -> str:
        """URL to the cover image of the song."""
        return f"{self.URL}/data/cover/{self.id}.jpg"

    def search_youtube_link(self) -> str | None:
        """Extract the first YouTube link from the comments.
        Typically, the TXT file and the GAP are synced for this version of the song."""
        with requests.get(f"{self.url}", timeout=30) as response:
            if response.ok:
                page_html = response.content.decode("utf-8")
                match = re.search(r"youtube.com/embed/([\w_-]+)", page_html)
                if match:
                    return match.group(1)
        return None
