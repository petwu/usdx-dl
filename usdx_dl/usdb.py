"""UltraStar DataBase API client."""

import html
import re
from typing import Final

import requests
from yt_dlp.cookies import (
    SUPPORTED_BROWSERS,
    _LinuxKeyring,
    extract_cookies_from_browser,
)

from usdx_dl import models


class APIClient:
    """Simple wrapper to query https://usdb.animux.de."""

    URL: Final[str] = "https://usdb.animux.de"
    DOMAIN: Final[str] = "usdb.animux.de"
    SESSION_COOKIE_NAME: Final[str] = "PHPSESSID"

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
        if not cookie.startswith(f"{self.SESSION_COOKIE_NAME}="):
            cookie = f"{self.SESSION_COOKIE_NAME}={cookie}"

        self.id = usdb_id
        self.url = f"{self.URL}/?link=detail&id={self.id}"
        self.cookie = cookie
        self.headers = {
            "Cookie": self.cookie,
            # I don't think this has any effect. Users can set their language preference
            # in the settings and the page will be translated accordingly. For
            # non-logged in requests, the language seems to be mostly English.
            # Some parts seem to be missing translations.
            "Accept-Language": "en",
        }

    def get_username(self, timeout: int = 30) -> str | None:
        """Check if the cookie is valid.

        Returns:
            None if the cookie is invalid, or the username of the logged in user.
        """
        with requests.get(
            f"{self.URL}/?link=profil",  # cSpell: disable-line
            headers=self.headers,
            timeout=timeout,
        ) as response:
            page_html = response.content.decode("utf-8")
        # try to extract the username from the tracker script
        # (it appears in other places too, but the extraction is more complicated
        # and language dependent)
        match = re.search(
            r"_paq.push[(\['\"\s]+setUserId['\"\s,]+(?P<username>[^'\"]+)['\"]",
            page_html,
        )
        if match:
            return match.group("username")

        return None

    def fetch_txt(self, timeout: int = 30) -> str | None:
        """Download the TXT file."""
        with requests.post(
            f"{self.URL}/?link=gettxt&id={self.id}",
            headers=self.headers,
            data={"wd": "1"},
            timeout=timeout,
        ) as response:
            page_html = response.content.decode("utf-8")
        # NOTE: responses for non-logged in users are mostly localized in English
        if re.search(r"(please login|not logged in)", page_html, re.IGNORECASE):
            raise RuntimeError(
                f"Failed to fetch TXT file for {self.url}. "
                f"The {self.SESSION_COOKIE_NAME} cookie is invalid or expired."
            )
        # NOTE: this string seems to be always in German even if the user has set a
        # different language preference
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


def find_sessions(
    profile: str | None = None,
    # cSpell: disable-next-line
    keyring: _LinuxKeyring | None = None,
) -> list[models.USDBSession]:
    """Find all logged-in USDB sessions from supported browsers.

    Args:
        profile: Optional browser profile name to search for. If None, the most recently
            accessed profile will be used.
        keyring: Optional keyring to use for decrypting chromium cookies on Linux.
            If None, guesses the keyring based on the desktop environment, which should
            work in most cases.

    Returns:
        A list of session objects.
    """
    results: list[models.USDBSession] = []
    for browser_name in SUPPORTED_BROWSERS:
        try:
            # use yt-dlp's cookies-from-browser feature to extract cookies from all major browsers
            cookie_jar = extract_cookies_from_browser(
                browser_name,
                profile=profile,
                keyring=keyring,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            continue
        for cookie in cookie_jar:
            if (
                cookie.domain.endswith(APIClient.DOMAIN)
                and cookie.name == APIClient.SESSION_COOKIE_NAME
                and cookie.value
            ):
                break
        else:
            continue
        username = APIClient(0, cookie.value).get_username()
        if not username:
            continue
        results.append(
            models.USDBSession(
                browser=browser_name,
                username=username,
                cookie=cookie.value,
            )
        )
    return results


def check(cookie: str) -> models.USDBSession | None:
    """Check if a USDB cookie is valid."""
    username = APIClient(0, cookie).get_username()
    if not username:
        return None
    return models.USDBSession(
        browser="manual",
        username=username,
        cookie=cookie,
    )
