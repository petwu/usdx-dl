"""Basic speed test."""
# cSpell: ignore urandom KHTML Referer

import os
from pathlib import Path
from time import perf_counter

import requests

from usdx_dl import ansi

DOWNLOAD_URL = "https://speed.cloudflare.com/__down?bytes=%d"
UPLOAD_URL = "https://speed.cloudflare.com/__up"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
    "Accept": "*/*",
    "Accept-Language": "en",
    "Accept-Encoding": "gzip",
    "Referer": "https://speed.cloudflare.com/",
}


def download(num_bytes: int = 10_000_000, cache_path: Path | None = None) -> float:
    """Estimate download speed in B/s. If you plan to call this function regularly,
    consider caching the result to prevent being rate-limited (HTTP 429)."""
    url = DOWNLOAD_URL % num_bytes
    start = perf_counter()
    with requests.get(url, headers=HEADERS, timeout=15) as response:
        if not response.ok and cache_path and cache_path.is_file():
            try:
                return float(cache_path.read_text(encoding="utf-8"))
            except (ValueError, FileNotFoundError):
                pass
        response.raise_for_status()
        data = response.content
    elapsed = perf_counter() - start
    speed = len(data) / elapsed
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(str(speed), encoding="utf-8")
    return speed


def upload(num_bytes: int = 5_000_000, cache_path: Path | None = None) -> float:
    """Estimate upload speed in B/s. If you plan to call this function regularly,
    consider caching the result to prevent being rate-limited (HTTP 429)."""
    url = UPLOAD_URL
    data = os.urandom(num_bytes)
    start = perf_counter()
    with requests.post(url, data=data, headers=HEADERS, timeout=15) as response:
        if not response.ok and cache_path and cache_path.is_file():
            try:
                return float(cache_path.read_text(encoding="utf-8"))
            except (ValueError, FileNotFoundError):
                pass
        response.raise_for_status()
    elapsed = perf_counter() - start
    speed = len(data) / elapsed
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(str(speed), encoding="utf-8")
    return speed


if __name__ == "__main__":
    print(f"{ansi.BOLD}Speedtest{ansi.RESET}")
    print(f"{ansi.DIM}Download...", end="", flush=True)
    down = download()
    print(f"\r{ansi.CYAN}Download: {down / 2**20:6.2f} MiB/s{ansi.RESET}")
    print(f"{ansi.DIM}Upload...", end="", flush=True)
    up = upload()
    print(f"\r{ansi.MAGENTA}Upload:   {up / 2**20:6.2f} MiB/s{ansi.RESET}")
