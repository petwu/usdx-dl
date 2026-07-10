import hashlib
import itertools
import platform
import shutil
import tempfile
from pathlib import Path

import pytest
import requests

from usdx_dl import __app_name__, platform_utils, required_tools


@pytest.fixture(scope="module", autouse=True)
def fixture():
    """Module-level fixture."""
    temp_dir = Path(tempfile.gettempdir()) / f"{__app_name__}-test"
    shutil.rmtree(temp_dir, ignore_errors=True)

    # patch the bin_path function to return a temporary directory
    required_tools.bin_path = patched_bin_path

    # skip if offline
    try:
        requests.get("https://www.google.com", timeout=5)
    except requests.ConnectionError:
        pytest.skip("No internet connection")

    yield

    # cleanup temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)


def patched_bin_path(name: str | None = None) -> Path:
    """Patch the bin_path function to return a temporary directory."""
    os_name = platform.system()
    arch = platform_utils.arch()
    path = Path(tempfile.gettempdir()) / f"{__app_name__}-test/{os_name}/{arch}/bin"
    if name is not None:
        path = path / f"{name}{'.exe' if platform.system() == 'Windows' else ''}"
    return path


@pytest.mark.parametrize(
    "tool_name,os_name,arch",
    list(
        itertools.product(
            ["ffmpeg", "ffprobe", "deno"],
            ["Linux", "Windows", "Darwin"],
            [platform_utils.Arch.X86_64, platform_utils.Arch.ARM64],
        )
    ),
)
@pytest.mark.slow
def test_download(tool_name: str, os_name: str, arch: platform_utils.Arch) -> None:
    """Test downloading a required tool."""
    platform.system = lambda: os_name
    platform_utils.arch = lambda: arch

    required_tools.download(tool_name, force=True)

    expected_output_path = required_tools.bin_path(tool_name)
    assert expected_output_path.exists(), (
        f"Expected {expected_output_path} to exist after download."
    )
    assert expected_output_path.is_file(), (
        f"Expected {expected_output_path} to be a file after download."
    )
    assert expected_output_path.stat().st_size > 0, (
        f"Expected {expected_output_path} to be non-empty after download."
    )

    spec = next((s for s in required_tools.__TOOLS__ if s.name == tool_name), None)
    assert spec is not None
    download_info = spec.downloads[(os_name, arch)]

    sha256 = hashlib.sha256(expected_output_path.read_bytes()).hexdigest()
    expected_sha256 = download_info.member_sha256
    assert sha256 == expected_sha256, (
        f"SHA256 mismatch for {tool_name} on {os_name}/{arch}: "
        f"expected {expected_sha256}, got {sha256}."
    )
