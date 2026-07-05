"""Platform-specific utility functions."""

# pylint: disable=no-member,no-name-in-module,import-outside-toplevel,import-error,broad-exception-caught
# mypy: disable-error-code="attr-defined"
# pyright: reportAttributeAccessIssue=none
# cSpell: disable

import os
import platform
import shutil
import subprocess
from collections.abc import Sequence
from enum import StrEnum
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

    match platform.system():
        case "Darwin":  # macOS
            subprocess.call(("open", path))
        case "Windows":
            os.startfile(path)
        case "Linux":
            subprocess.call(("xdg-open", path))
        case _:
            raise OSError(f"Unsupported platform: {platform.system()}")


def is_dark_mode() -> bool:
    """Check if the system is in dark mode.

    Returns:
        True if the system is in dark mode, False otherwise.
    """
    match platform.system():
        case "Darwin":  # macOS
            try:
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return result.stdout.strip().lower() == "dark"
            except Exception:
                return False
        case "Windows":
            try:
                import winreg

                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(
                    registry,
                    "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
            except Exception:
                return False
        case "Linux":
            try:
                # gsettings should be part of the glib package on most distros and installed
                # as dependency of some package (e.g. gtk, firefox, chromium, ffmpeg, gimp,
                # networkmanager, pipewire, qt6-base, xdg-desktop-portal, libportal, ...)
                # on most desktop environments, not just GNOME
                if shutil.which("gsettings"):
                    result = subprocess.run(
                        [
                            "gsettings",
                            "get",
                            "org.gnome.desktop.interface",
                            "color-scheme",
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    return "dark" in result.stdout.lower()
                elif shutil.which("busctl"):
                    # busctl is part of systemd
                    result = subprocess.run(
                        [
                            "busctl",
                            "--user",
                            "call",
                            "org.freedesktop.portal.Desktop",
                            "/org/freedesktop/portal/desktop",
                            "org.freedesktop.portal.Settings",
                            "Read",
                            "ss",
                            "org.freedesktop.appearance",
                            "color-scheme",
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    return "dark" in result.stdout.lower()
                else:
                    return False
            except Exception:
                return False
        case _:
            return False


def file_dialog(
    title: str | None = None,
    filters: Sequence[str] | None = None,
    default: str | None = None,
    directory: bool = False,
) -> Path | None:
    """Open a file or directory selection dialog.

    Args:
        title: The title of the dialog.
        filters: The file filters to apply (e.g., ["Text files (*.txt)", "All files (*)"]).
        default: The default path to open in the dialog.
        directory: If True, open a directory selection dialog. Otherwise, open a file
            selection dialog.

    Returns:
        The selected file or directory path, or None if the dialog was canceled.
    """
    from qtpy.QtWidgets import QApplication, QFileDialog

    _ = QApplication.instance() or QApplication([])

    dialog = QFileDialog()

    if title:
        dialog.setWindowTitle(title)

    if filters:
        dialog.setNameFilters(filters)

    if default:
        dialog.setDirectory(default)

    if directory:
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    else:
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

    if dialog.exec():
        return Path(dialog.selectedFiles()[0])

    return None


class Arch(StrEnum):
    """CPU architecture."""

    X86 = "x86"
    X86_64 = "x86_64"
    ARM = "arm"
    ARM64 = "arm64"
    OTHER = "other"


def arch() -> Arch:
    """Get the CPU architecture of the current system.

    Returns:
        The CPU architecture as an Arch enum member.
    """
    match platform.machine().lower():
        case "x86" | "i386" | "i686":
            return Arch.X86
        case "x86_64" | "amd64":
            return Arch.X86_64
        case "arm" | "armv6l" | "armv7l" | "armv8l":
            return Arch.ARM
        case "aarch64" | "arm64":
            return Arch.ARM64
        case _:
            return Arch.OTHER
