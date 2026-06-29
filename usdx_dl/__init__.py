import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

from platformdirs import PlatformDirs

try:
    __version__ = version("usdx_dl")
except PackageNotFoundError:
    pyproject_toml = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_toml.exists():
        with open(pyproject_toml, "rb") as f:
            __version__ = tomllib.load(f)["project"]["version"]
    else:
        __version__ = "unknown"

__app_name__ = "usdx-dl"
__app__: Final[PlatformDirs] = PlatformDirs(__app_name__)
