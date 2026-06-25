# pylint: disable=no-member
# mypy: disable-error-code="attr-defined"
# pyright: reportAttributeAccessIssue=none
# cSpell: disable

import os
import platform
import subprocess
from pathlib import Path


def open_with_default_app(path: Path | str) -> None:
    """Open a file or directory with the default application for the platform.

    Args:
        path: The path to the file or directory to open.

    Raises:
        FileNotFoundError: If the specified path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file or directory: {path}")

    if platform.system() == "Darwin":  # macOS
        subprocess.call(("open", path))
    elif platform.system() == "Windows":  # Windows
        os.startfile(path)
    else:  # Linux
        subprocess.call(("xdg-open", path))
