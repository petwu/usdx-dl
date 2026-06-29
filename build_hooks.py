"""https://hatch.pypa.io/dev/plugins/build-hook/reference"""
# pylint: disable=unused-argument

import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def is_npm_available() -> bool:
    """Check if npm is available in the system."""
    try:
        subprocess.run(
            ["npm", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def build_web_ui(version: str, build_data: dict[str, Any]) -> None:
    """Build the web UI using npm/vite."""
    web_dir = Path(__file__).parent / "usdx_dl" / "web" / "ui"
    dist_dir = web_dir / "dist"

    if not is_npm_available():
        raise RuntimeError("npm is not available. Please install Node.js and npm.")

    subprocess.run(["npm", "install"], cwd=web_dir, check=True)
    subprocess.run(["npm", "run", "build"], cwd=web_dir, check=True)

    build_data["force_include"] = {str(dist_dir): "usdx_dl/web/ui/dist"}
    build_data["force_include_editable"] = {str(dist_dir): "usdx_dl/web/ui/dist"}


class BuildHook(BuildHookInterface):
    """Custom build hook."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        build_web_ui(version, build_data)
