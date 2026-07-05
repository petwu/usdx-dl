"""ANSI color codes."""
# pylint: disable=global-statement

import os
import platform
import sys

RESET = "\033[0m"
BLACK = "\033[0;30m"
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE = "\033[0;34m"
MAGENTA = "\033[0;35m"
CYAN = "\033[0;36m"
WHITE = "\033[0;37m"

BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINKING = "\033[5m"
INVERSE = "\033[7m"
HIDDEN = "\033[8m"
STRIKETHROUGH = "\033[9m"


def __getattr__(name: str) -> str:
    if name not in globals():
        raise AttributeError(f"module {__name__} has no attribute {name}")

    value = globals()[name]
    if not isinstance(value, str) or not value.startswith("\033["):
        return value
    if (
        not sys.stdout.isatty()  #
        and os.environ.get("FORCE_COLOR", "0").lower() not in ("1", "true", "yes")
        or os.environ.get("NO_COLOR", "0").lower() in ("1", "true", "yes")
    ):
        return ""

    return value


def force_color() -> None:
    """Force ANSI color codes to be enabled."""
    # cSpell: ignore CLICOLOR
    os.environ["FORCE_COLOR"] = "1"
    os.environ["CLICOLOR_FORCE"] = "1"
    os.environ["CLICOLOR"] = "1"
    os.environ["AV_LOG_FORCE_COLOR"] = "1"  # ffmpeg


def color_enabled() -> bool | None:
    """Check if ANSI color codes are enabled."""
    no_color = os.getenv("NO_COLOR", "0").lower() in ("1", "true", "yes")
    if no_color:
        return False
    force = os.getenv("FORCE_COLOR", "0").lower() in ("1", "true", "yes")
    if force:
        return True
    return None


if sys.stdout.isatty():
    if platform.system() == "Windows":
        kernel32 = __import__("ctypes").windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        del kernel32
