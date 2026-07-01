"""Utility functions for checking and downloading required 3rd-party CLI tools."""

import os
import platform
import re
import shutil
import subprocess
import tarfile
import time
import zipfile
from pathlib import Path

import requests
from packaging.version import Version

from usdx_dl import __app__, ansi
from usdx_dl.models import Tool

__all__ = ["private_bin_dir", "query", "missing", "download"]


def private_bin_dir() -> Path:
    """Return the path to the app-private bin directory."""
    return __app__.user_data_path / "bin"


def query() -> list[Tool]:
    """Return a list of all required tools."""
    bin_dir = private_bin_dir()

    ffmpeg_path = Path(shutil.which("ffmpeg") or bin_dir / "ffmpeg")
    ffmpeg = __query_ffmpeg(ffmpeg_path, bin_dir / "ffmpeg_latest.txt")

    return [ffmpeg]


def missing() -> list[Tool]:
    """Return a list of missing required programs."""
    return [tool for tool in query() if tool.version is None]


def download() -> None:
    """Download missing tool binaries."""
    for tool in query():
        if tool.path.exists() and tool.version and tool.version >= tool.latest:
            continue
        print(f"{ansi.BOLD}Downloading {tool.name}{ansi.RESET}")
        print(f"{ansi.DIM}Current version: {tool.version}{ansi.RESET}")
        print(f"{ansi.DIM}Latest version: {tool.latest}{ansi.RESET}")
        print(f"{ansi.DIM}URL: {tool.download_url}{ansi.RESET}")
        print(f"{ansi.DIM}Destination: {tool.path}{ansi.RESET}")
        assert tool.path is not None
        tool.path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(tool.download_url, stream=True, timeout=30) as response:
            response.raise_for_status()
            with open(tool.path, "wb") as f:
                shutil.copyfileobj(response.raw, f)
            __extract_if_necessary(tool)
            os.chmod(tool.path, 0o755)


def __extract_if_necessary(tool: Tool) -> None:
    """Unpack the downloaded file if it's an archive (zip/tar)."""
    archive_path = tool.path
    if not archive_path.exists():
        return

    if (tool.name, platform.system()) not in [
        ("ffmpeg", "Linux"),
    ]:
        return

    member_name = tool.name if platform.system() != "Windows" else f"{tool.name}.exe"
    if zipfile.is_zipfile(archive_path):
        archive_path = archive_path.rename(archive_path.with_suffix(".tmp.zip"))
        with zipfile.ZipFile(archive_path, "r") as archive:
            member = next(
                (
                    m.filename
                    for m in archive.infolist()
                    if not m.is_dir() and m.filename == member_name
                ),
                None,
            )
            if member is None:
                raise RuntimeError(f"Could not find {member_name} in the zip archive")
            archive.extract(member, path=archive_path.parent)
        archive_path.unlink()
        extracted_path = archive_path.parent / member
        if extracted_path != tool.path:
            extracted_path.rename(tool.path)
        if extracted_path.parent != tool.path.parent:
            shutil.rmtree(extracted_path.parent, ignore_errors=True)
    elif tarfile.is_tarfile(archive_path):
        archive_path = archive_path.rename(archive_path.with_suffix(".tmp.tar"))
        with tarfile.open(archive_path, "r:*") as archive:
            member = next(
                (
                    m.name
                    for m in archive.getmembers()
                    if m.isfile() and member_name == Path(m.name).name
                ),
                None,
            )
            if member is None:
                raise RuntimeError(f"Could not find {member_name} in the tar archive")
            print(f"Extracting {member} from tar archive to {archive_path.parent}")
            archive.extract(member, path=archive_path.parent)
        archive_path.unlink()
        extracted_path = archive_path.parent / member
        if extracted_path != tool.path:
            extracted_path.rename(tool.path)
        if extracted_path.parent != tool.path.parent:
            shutil.rmtree(extracted_path.parent, ignore_errors=True)
    else:
        pass


def __query_ffmpeg(
    ffmpeg_path: Path,
    latest_cache: Path,
    cache_age: int = 86400,  # 1 day in seconds
) -> Tool:
    """Query ffmpeg tool information."""
    now = time.time()
    if latest_cache.exists() and latest_cache.stat().st_mtime > now - cache_age:
        cache = latest_cache.read_text(encoding="utf-8").splitlines()[:2]
        latest = Version(cache[0])
        latest_year = Version(cache[1]) if len(cache) > 1 and cache[1] else None
    else:
        url = "https://ffmpeg.org/download.html"
        with requests.get(url, timeout=10) as response:
            html = response.text
        match = re.search(r"ffmpeg-(\d+\.\d+\.\d+)\.tar\.xz", html)
        if not match:
            raise RuntimeError("Could not find FFmpeg version")
        latest = Version(match.group(1))
        match = re.search(r"release.+(\d{4})-(\d{2})-(\d{2})", html)
        latest_year = None
        if match:
            year, month, day = match.groups()
            latest_year = Version(f"{year}.{month}.{day}")
        latest_cache.parent.mkdir(parents=True, exist_ok=True)
        latest_cache.write_text(f"{latest}\n{latest_year or ''}", encoding="utf-8")

    current = None
    try:
        result = subprocess.run(
            [str(ffmpeg_path), "-version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = result.stdout.decode("utf-8")
        match = re.search(r"ffmpeg version \w+(\d+\.\d+\.\d+)", output)
        if match:
            current = Version(match.group(1))
        else:
            # master builds of ffmpeg don't have a version number but a build commit + date
            match = re.search(r"ffmpeg version [\w-]+(\d{4})(\d{2})(\d{2})", output)
            if match and latest_year:
                year, month, day = match.groups()
                current = Version(f"{year}.{month}.{day}")
                latest = latest_year
    except FileNotFoundError:
        pass
    except OSError as e:
        if e.errno == 8:  # Exec format error
            ffmpeg_path.unlink()

    os_name = platform.system()
    os_arch = platform.machine().lower()
    if os_arch not in ["x86_64", "amd64"]:
        raise NotImplementedError(f"Unsupported architecture: {os_arch}")
    match os_name:
        case "Linux":
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"  # pylint: disable=line-too-long
        case "Darwin":
            url = f"https://evermeet.cx/ffmpeg/ffmpeg-{latest}.zip"
        case "Windows":
            url = f"https://www.gyan.dev/ffmpeg/ffmpeg-{latest}.zip"
        case _:
            raise NotImplementedError(f"Unsupported OS: {os_name}")

    return Tool(
        name="ffmpeg",
        path=ffmpeg_path,
        version=str(current) if current else None,
        latest=str(latest),
        download_url=url,
        homepage="https://ffmpeg.org",
    )
