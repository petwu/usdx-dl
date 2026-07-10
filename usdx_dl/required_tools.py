"""Utility functions for checking and downloading required 3rd-party CLI tools."""

import hashlib
import io
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests
from packaging.version import Version

from usdx_dl import __app__, ansi, platform_utils
from usdx_dl.func_utils import mtime_cache
from usdx_dl.models import DownloadInfo, Tool
from usdx_dl.platform_utils import Arch
from usdx_dl.types import ProgressCallback

__all__ = ["bin_path", "query", "query_all", "missing", "download"]


@dataclass(frozen=True)
class ToolSpec:
    """Information about a required tool."""

    name: str
    reason: str
    required: Version
    homepage: str
    repository: str
    provider: str | None
    license: str
    license_url: str
    downloads: dict[tuple[str, Arch], DownloadInfo]
    version_flag: str
    version_regex: str


__TOOLS__ = [
    # pylint: disable=line-too-long,unnecessary-lambda
    ToolSpec(
        name="ffmpeg",
        reason=textwrap.dedent("""
        Used for processing audio and video files. E.g. used for extracting audio from video files,
        converting between different audio/video formats and various post-processing tasks.
        Required by [`yt-dlp`](https://github.com/yt-dlp/yt-dlp#dependencies).
        """),
        required=Version("8.0.0"),
        homepage="https://ffmpeg.org",
        repository="https://github.com/FFmpeg/FFmpeg",
        provider="https://github.com/BtbN/FFmpeg-Builds",
        license="GPLv3",
        license_url="https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md",
        downloads={
            ("Linux", Arch.X86_64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-linux64-gpl-8.1.tar.xz",
                sha256="7aadf7d95d94e9dc71d4283d64be209ef1ba4cab5eb09893c29037223704d0b1",
                member="bin/ffmpeg",
                member_sha256="93531b77ee9c3688272f7e24893316264d97573239816e9f4763f00428b7b07a",
            ),
            ("Linux", Arch.ARM64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-linuxarm64-gpl-8.1.tar.xz",
                sha256="147400f5b6fd2486523f0b010191b5d5c58aaa44c56a296cbd1a3f130cb59329",
                member="bin/ffmpeg",
                member_sha256="7dc22466f3e60fcc93241e1f8e418d3e029dea511505e74a5be7d0fc18269e2e",
            ),
            ("Windows", Arch.X86_64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-win64-gpl-8.1.zip",
                sha256="68d17ffe72af5254c9ef3912b7ef5d7dae2c01e9006debfdc2279737d8fb0161",
                member="bin/ffmpeg.exe",
                member_sha256="78fbca59a0afe33cad16309ed277359a92b53ba7868a593d351b850158df6a54",
            ),
            ("Windows", Arch.ARM64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-winarm64-gpl-8.1.zip",
                sha256="c0b38810a44d5a8af96fe43117e4263d288ab3957c3d95d7cc6e6af5dc32d5f2",
                member="bin/ffmpeg.exe",
                member_sha256="38ea9cb8741517995f3f83ac9cc98c6d8ee8406cd2a3581f0694d49eb1065c4b",
            ),
            ("Darwin", Arch.X86_64): DownloadInfo(
                version="8.1.2",
                url="https://ffmpeg.martin-riedl.de/download/macos/amd64/1783018342_8.1.2/ffmpeg.zip",
                sha256="a52ef43883f44c219766d4b3bdde4e635b35465d0b704c01c3a0566b59775df9",
                member="ffmpeg",
                member_sha256="1ca59dda73668c59898a0b305afd8a88817a989187f222ec62d64e775d614d23",
            ),
            ("Darwin", Arch.ARM64): DownloadInfo(
                version="8.1.2",
                url="https://ffmpeg.martin-riedl.de/download/macos/arm64/1783011502_8.1.2/ffmpeg.zip",
                sha256="ef1aa60006c7b77ce170c1608c08d8e4ba1c30c5746f2ac986ded932d0ac2c3c",
                member="ffmpeg",
                member_sha256="eaf91238e104dd0e262bc6510e25061855cc99a6955a721b0ac99660d58c473d",
            ),
        },
        version_flag="-version",
        version_regex=r"ffmpeg version (\w+(?P<semver>\d+\.\d+\.\d+)|[\w-]+(?P<calver>\d{4}\d{2}\d{2}))",
    ),
    ToolSpec(
        name="ffprobe",
        reason=textwrap.dedent("""
        Used for probing audio and video files. E.g. used for extracting metadata from audio/video files.
        Required by [`yt-dlp`](https://github.com/yt-dlp/yt-dlp#dependencies).
        """),
        required=Version("8.0.0"),
        homepage="https://ffmpeg.org",
        license="GPLv3",
        license_url="https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md",
        repository="https://github.com/FFmpeg/FFmpeg",
        provider="https://github.com/BtbN/FFmpeg-Builds",
        downloads={
            ("Linux", Arch.X86_64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-linux64-gpl-8.1.tar.xz",
                sha256="7aadf7d95d94e9dc71d4283d64be209ef1ba4cab5eb09893c29037223704d0b1",
                member="bin/ffprobe",
                member_sha256="4fa0fe276aaf4e1085ced0b771c35d298ddd11a0cfe8869ee794e13b4622b454",
            ),
            ("Linux", Arch.ARM64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-linuxarm64-gpl-8.1.tar.xz",
                sha256="147400f5b6fd2486523f0b010191b5d5c58aaa44c56a296cbd1a3f130cb59329",
                member="bin/ffprobe",
                member_sha256="c0c99da586f9d8ebcd64a91b8c317f44deb3fc74679765cfb8fb469910119713",
            ),
            ("Windows", Arch.X86_64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-win64-gpl-8.1.zip",
                sha256="68d17ffe72af5254c9ef3912b7ef5d7dae2c01e9006debfdc2279737d8fb0161",
                member="bin/ffprobe.exe",
                member_sha256="a93b061d797a0e0dcb42968515e3b5d78e5624fc7c76ee507e2361fcbefdc7c6",
            ),
            ("Windows", Arch.ARM64): DownloadInfo(
                version="8.1.2",
                url="https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-07-03-13-21/ffmpeg-n8.1.2-21-gce3c09c101-winarm64-gpl-8.1.zip",
                sha256="c0b38810a44d5a8af96fe43117e4263d288ab3957c3d95d7cc6e6af5dc32d5f2",
                member="bin/ffprobe.exe",
                member_sha256="64172b7ac20fdeaf60a964a99f9fad3a4850d8484cba604ae1424c75f5a193e6",
            ),
            ("Darwin", Arch.X86_64): DownloadInfo(
                version="8.1.2",
                url="https://ffmpeg.martin-riedl.de/download/macos/amd64/1783018342_8.1.2/ffprobe.zip",
                sha256="5408ca588c8c72b0dde3afe676d0a7acf25ef97e55ae6eba5c7bede1cda42695",
                member="ffprobe",
                member_sha256="bdb6aff0f1f414382effd97040f7862dc85e67996ac296cb4288beed0e06498f",
            ),
            ("Darwin", Arch.ARM64): DownloadInfo(
                version="8.1.2",
                url="https://ffmpeg.martin-riedl.de/download/macos/arm64/1783011502_8.1.2/ffprobe.zip",
                sha256="c39787f4af7a3932502d2d48db6f6feaaa836b48a73ef78c32cc3285df61dfaf",
                member="ffprobe",
                member_sha256="ed9dc5871914b466b96b402c9ec0ba68ce4f836e72faa464b1b4e279835bd4a6",
            ),
        },
        version_flag="-version",
        version_regex=r"ffprobe version (\w+(?P<semver>\d+\.\d+\.\d+)|[\w-]+(?P<calver>\d{4}\d{2}\d{2}))",
    ),
    ToolSpec(
        name="deno",
        reason=textwrap.dedent("""
        A JavaScript runtime. Required by [`yt-dlp`](https://github.com/yt-dlp/yt-dlp#dependencies)
        for full YouTube support.
        """),
        required=Version("2.3.0"),  # https://github.com/yt-dlp/ejs#runtime-requirements
        homepage="https://deno.land",
        repository="https://github.com/denoland/deno",
        provider=None,
        license="MIT",
        license_url="https://github.com/denoland/deno/blob/main/LICENSE.md",
        downloads={
            ("Linux", Arch.X86_64): DownloadInfo(
                version="2.9.1",
                url="https://dl.deno.land/release/v2.9.1/deno-x86_64-unknown-linux-gnu.zip",
                sha256="710c54d63477d1100844ef4818f19507ce0dbf40510903b1d883f19e394446a2",
                member="deno",
                member_sha256="b800d071246591b733221412747ac7bc5f80c07098416a0cb2a4284508a9d312",
            ),
            ("Linux", Arch.ARM64): DownloadInfo(
                version="2.9.1",
                url="https://dl.deno.land/release/v2.9.1/deno-aarch64-unknown-linux-gnu.zip",
                sha256="0a60d079fa79635a59803074dbbfe86ccc35746dc2c4f8d73f2e50338b3283a9",
                member="deno",
                member_sha256="15ec8a2e6e45fea2501c42ee32aee918d886fac4ab4ef22316c53ad3e6da2cfc",
            ),
            ("Windows", Arch.X86_64): DownloadInfo(
                version="2.9.1",
                url="https://dl.deno.land/release/v2.9.1/deno-x86_64-pc-windows-msvc.zip",
                sha256="ab310b4232cca207d40ffa41867e93aaf9f893802bc76756e74f486a6b21b371",
                member="deno.exe",
                member_sha256="3819117e301d48a6931f9a1a4fb5e4a10c464163189bcff8fce5d75025d6f2a0",
            ),
            ("Windows", Arch.ARM64): DownloadInfo(
                version="2.9.1",
                url="https://dl.deno.land/release/v2.9.1/deno-x86_64-pc-windows-msvc.zip",  # emulated
                sha256="ab310b4232cca207d40ffa41867e93aaf9f893802bc76756e74f486a6b21b371",
                member="deno.exe",
                member_sha256="3819117e301d48a6931f9a1a4fb5e4a10c464163189bcff8fce5d75025d6f2a0",
            ),
            ("Darwin", Arch.X86_64): DownloadInfo(
                version="2.9.1",
                url="https://dl.deno.land/release/v2.9.1/deno-x86_64-apple-darwin.zip",
                sha256="89cbc8c974247772d9200724741b4e692ef49fe470b2ff555da905817c3daa11",
                member="deno",
                member_sha256="dc1a009cc6a232a8452ca8248b652e2239aac7d8be53bd7f4f9d01f6eb5272d5",
            ),
            ("Darwin", Arch.ARM64): DownloadInfo(
                version="2.9.1",
                url="https://dl.deno.land/release/v2.9.1/deno-aarch64-apple-darwin.zip",
                sha256="ee3473502118eab301eca93aa6b31d6b0b6c1602d0f59e4cb89d4a262b12f6e7",
                member="deno",
                member_sha256="df5e2cca5253ec99b9a630fb059bf01cdbbf586fed1f344017875c5462b2c483",
            ),
        },
        version_flag="-version",
        version_regex=r"deno v?(?P<semver>\d+\.\d+\.\d+)",
    ),
]


def bin_path(name: str | None = None) -> Path:
    """Path to the app-private bin directory or a specific tool binary.

    Args:
        name: The name of the tool binary to return the path for.

    Returns:
        The path to the app-private bin directory or a specific tool binary.
    """
    path = __app__.user_data_path / "bin"
    if name is not None:
        path = path / f"{name}{'.exe' if platform.system() == 'Windows' else ''}"
    return path


def query(name: str) -> Tool:
    """Query tool information."""

    download_path = bin_path(name)
    os_name = platform.system()
    arch = platform_utils.arch()
    tool_spec = next((t for t in __TOOLS__ if t.name == name), None)
    if tool_spec is None:
        raise RuntimeError(f"No tool info found for {name}.")
    download_info = tool_spec.downloads.get((os_name, arch))
    if download_info is None:
        raise RuntimeError(f"No {name} download available for {os_name} {arch.value}.")

    current: Version | None = None
    path: Path | str | None = None
    if os.getenv("USDX_DL_NO_SYSTEM_TOOLS", "").lower() not in ("1", "true", "yes"):
        path = shutil.which(name)
    if path is not None:
        path = Path(path)
        current = tool_version(path, tool_spec.version_flag, tool_spec.version_regex)
    if path is None or current is None or current < tool_spec.required:
        path = download_path
        current = tool_version(path, tool_spec.version_flag, tool_spec.version_regex)

    download_required = (
        current is None  # tool not found
        or current < tool_spec.required  # tool version is too old
        or (
            # not using the system-installed version and the sha256 doesn't match,
            # i.e. old version or corrupted download
            path == download_path
            and (
                not download_path.exists()
                or hashlib.sha256(download_path.read_bytes()).hexdigest()
                != download_info.member_sha256
            )
        )
    )

    return Tool(
        name=name,
        reason=tool_spec.reason,
        path=path,
        version=str(current) if current else None,
        download_required=download_required,
        download_path=download_path,
        download_info=download_info,
        homepage=tool_spec.homepage,
        repository=tool_spec.repository,
        provider=tool_spec.provider,
        license=tool_spec.license,
        license_url=tool_spec.license_url,
    )


def query_all() -> list[Tool]:
    """Return a list of all required tools."""
    return [query(tool.name) for tool in __TOOLS__]


def missing() -> list[Tool]:
    """Return a list of missing required programs."""
    return [tool for tool in query_all() if tool.version is None]


def download(
    name: str | None = None,
    force: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Download missing tool binaries."""
    for tool in [query(name)] if name else query_all():
        if tool.download_required or force:
            _download_tool(tool, progress_callback)


class _ProgressFileIO(io.FileIO):
    def __init__(self, path, mode="r", *, progress_callback):
        super().__init__(path, mode)
        self.progress_callback = progress_callback
        self.total_size = os.path.getsize(path)
        self.read_size = 0

    def read(self, size: int | None = -1) -> bytes:
        chunk = super().read(size)
        if chunk:
            self.read_size += len(chunk)
            progress = min(self.read_size / self.total_size, 1.0)
            self.progress_callback(progress)
        return chunk


def _download_tool(
    tool: Tool,
    progress_callback: ProgressCallback | None = None,
) -> None:
    print(f"{ansi.BOLD}Downloading {tool.name}{ansi.RESET}")
    print(f"{ansi.DIM}Version: {tool.download_info.version}{ansi.RESET}")
    print(f"{ansi.DIM}URL: {tool.download_info.url}{ansi.RESET}")
    print(f"{ansi.DIM}SHA256: {tool.download_info.sha256}{ansi.RESET}")
    print(f"{ansi.DIM}Destination: {tool.download_path}{ansi.RESET}")
    if progress_callback is None:
        progress_callback = lambda _: None  # noqa  # pylint: disable=unnecessary-lambda-assignment
    progress_callback(0.0)

    tool_dest = tool.download_path
    tool_dest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        download_dest = Path(tmpdir) / Path(tool.download_info.url).name
        # download the file
        buf = io.BytesIO()
        chunk_size = 8192
        with requests.get(tool.download_info.url, stream=True, timeout=30) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=chunk_size):
                buf.write(chunk)
                downloaded_size += len(chunk)
                if total_size:
                    progress_callback(downloaded_size / total_size * 0.8)
        buf.seek(0)

        # verify the SHA256 hash
        sha256 = hashlib.sha256(buf.getvalue()).hexdigest()
        if sha256 != tool.download_info.sha256:
            raise RuntimeError(
                f"SHA256 mismatch for {tool.name}: "
                f"expected {tool.download_info.sha256}, got {sha256}."
            )

        # save to disk
        with open(download_dest, "wb") as f:
            f.write(buf.getvalue())

        # extract the file
        progress_file = _ProgressFileIO(
            download_dest,
            "rb",
            progress_callback=lambda p: progress_callback(0.8 + p * 0.2),
        )
        is_zip = zipfile.is_zipfile(download_dest)
        is_tar = tarfile.is_tarfile(download_dest)
        if is_zip or is_tar:
            with (
                zipfile.ZipFile(progress_file)
                if is_zip
                else tarfile.open(fileobj=progress_file)
            ) as archive:
                if tool.download_info.member:
                    members = (
                        [m.filename for m in archive.infolist()]
                        if isinstance(archive, zipfile.ZipFile)
                        else [m.name for m in archive.getmembers()]  # pylint: disable=no-member
                    )
                    member = next(
                        (
                            m
                            for m in members
                            if m.replace("\\", "/").endswith(tool.download_info.member)
                        ),
                        None,
                    )
                    if member is None:
                        raise RuntimeError(
                            f"Could not find {tool.download_info.member} in the archive."
                        )
                    archive.extract(member, tool_dest.parent)
                    extracted_path = tool_dest.parent / member
                    extracted_path.rename(tool_dest)
                    for parent in extracted_path.parents:
                        if parent == tool_dest.parent:
                            break
                        try:
                            parent.rmdir()
                        except OSError:
                            break
                else:
                    archive.extractall(tool_dest.parent)
            # cleanup the downloaded archive
            download_dest.unlink(missing_ok=True)
        else:
            # assume it's a raw binary
            shutil.copy(download_dest, tool_dest)

        if not tool_dest.exists():
            raise RuntimeError(f"Failed to download {tool.name} to {tool_dest}.")

        os.chmod(tool_dest, 0o755)
        progress_callback(1.0)


@mtime_cache
def tool_version(path: Path | str, flag: str, regex: str) -> Version | None:
    """Determine the version of a tool at the given path.

    Args:
        path: The path to the tool binary.
        flag: The command-line flag to use to get the version (e.g., "--version").
        regex: A regex pattern to extract the version from the output.
            Must define a named group "version", "semver" or "calver" to capture the
            version string (in order of precedence).
    """
    if not Path(path).exists():
        return None
    try:
        result = subprocess.run(
            [str(path), flag],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError:
        return None
    output = result.stdout.decode("utf-8")
    match = re.search(regex, output)
    if match:
        groupdict = match.groupdict()
        version = (
            groupdict.get("version")
            or groupdict.get("semver")
            or groupdict.get("calver")
        )
        if version is None:
            raise ValueError(
                "Regex pattern must define a named group 'version', 'semver' "
                "and/or 'calver'."
            )
        return Version(version)
    return None
