"""Platform-specific utility functions."""

# pylint: disable=no-member,import-outside-toplevel,import-error,broad-exception-caught
# mypy: disable-error-code="attr-defined"
# pyright: reportAttributeAccessIssue=none
# cSpell: disable

import os
import platform
import shutil
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
