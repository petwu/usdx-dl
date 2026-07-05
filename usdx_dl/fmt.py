"""String formatting helpers."""

import math
import re
import unicodedata
from string import punctuation


def bytes(  # pylint: disable=redefined-builtin
    n: int,
    decimals: int = 2,
    si_unit: bool = False,
) -> str:
    """Convert bytes to a human-readable string.

    Args:
        n: Number of bytes. Must be non-negative.
        decimals: Number of decimal places to show.
        si_unit: If True, use SI units (kB, MB, etc.) with base 1000.
                 If False, use binary IEC units (KiB, MiB, etc.) with base 1024.

    Returns:
        Human-readable string like "1.50 MiB" or "1.50 MB".
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")

    base = 1000 if si_unit else 1024

    if si_unit:
        units = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB", "RB", "QB"]
    else:
        units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]

    if n < base:
        return f"{n} {units[0]}"

    exp = min(int(math.log(n, base)), len(units) - 1)
    value = n / (base**exp)

    return f"{value:.{decimals}f} {units[exp]}"


def time(seconds: float, decimals: int = 2, long_units: bool = False) -> str:
    """Convert seconds to a human-readable string.

    Args:
        seconds: Number of seconds. Must be non-negative.
        decimals: Number of decimal places to show for seconds.
        long_units: If True, use long units (seconds, minutes, hours).
                    If False, use short units (s, min, h).
    Returns:
        Human-readable string like "3d 17h 5min 17.34s".
    """
    if seconds < 0:
        raise ValueError(f"seconds must be non-negative, got {seconds}")

    if long_units:
        units = ["years", "months", "weeks", "days", "hours", "minutes", "seconds"]
    else:
        units = ["y", "mo", "w", "d", "h", "min", "s"]

    factors = [
        365.25 * 24 * 3600,  # years
        30.4375 * 24 * 3600,  # months
        7 * 24 * 3600,  # weeks
        24 * 3600,  # days
        3600,  # hours
        60,  # minutes
        1,  # seconds
    ]

    result = []
    for unit, factor in zip(units, factors):
        if unit == units[-1]:  # seconds
            result.append(f"{seconds:.{decimals}f}{unit}")
            break
        if seconds >= factor:
            value = int(seconds // factor)
            result.append(f"{value}{unit}")
            seconds -= value * factor

    if result:
        return " ".join(result)
    return f"0 {units[-1]}"


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """Return singular or plural form based on count."""
    if count == 1:
        return singular
    if plural is not None:
        return plural
    # simple pluralization by adding 's'
    return singular + "s"


def sub_diacritics(pattern: str, repl: str, string: str, **kwargs) -> str:
    """Like :func:`re.sub` but also matches diacritics.

    Example:
    >>> sub_diacritics(r"cafe", "bistro", "café")
    'bistro'
    >>> sub_diacritics(r"naive", "experienced", "naïve")
    'experienced'
    """
    # expand pattern to allow optional combining marks after each char
    expanded = "".join(
        f"{re.escape(ch)}[\u0300-\u036f\u1dc0-\u1dff\u20d0-\u20ff]*" for ch in pattern
    )
    nfd = unicodedata.normalize("NFD", string)
    result = re.sub(expanded, repl, nfd, **kwargs)
    return unicodedata.normalize("NFC", result)


def clean_title(title: str, artist: str) -> str:
    """Clean a song title by removing common prefixes/suffixes."""
    # remove quotes
    title = re.sub(r"[\"'“”‘’]", "", title)

    # remove leading/trailing artist names, e.g. "Artist - ", "... ft. Artist"
    for a in re.split(r"(,|&|and|feat\.?|ft\.?)", artist, flags=re.IGNORECASE):
        a = re.sub(r"[\"'“”‘’]", "", a.strip())
        if len(a) < 2:
            continue
        title = sub_diacritics(a, "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"^(.+)\s+(feat\.?|ft\.?)[\s\w-]+$", r"\1", title, flags=re.IGNORECASE
    )
    title = re.sub(r"\s+(feat\.?|ft\.?)", "", title, flags=re.IGNORECASE)

    # remove suffixes in braces/brackets, e.g. "(Official Music Video)"
    title = re.sub(r"(\([^)]+\)|\[[^]]+\])", "", title)

    # remove common extra words
    title = re.sub(
        r"(official|music|video|audio|lyric|lyrics|version|remastered|HD|4K|HQ|mono|stereo|m/v)",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # remove leading/trailing punctuation and whitespace
    title = re.sub(r"^[" + punctuation.replace("-", "\\-") + r"–—\s]+\s+", "", title)
    title = re.sub(r"\s+[" + punctuation.replace("-", "\\-") + r"–—\s]+$", "", title)
    title = title.strip()

    return title
