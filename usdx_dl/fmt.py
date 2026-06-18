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
