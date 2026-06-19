"""String formatting helpers."""

import math


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
