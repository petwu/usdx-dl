"""Function decorators and utilities."""

import inspect
import typing as t
from pathlib import Path


def mtime_cache[**P, R](func: t.Callable[P, R]) -> t.Callable[P, R]:
    """Decorator to cache the return value of a function based on the modification
    time of the first parameter annotated with :class:`pathlib.Path`.
    If the file is modified, the cache is invalidated.

    Example:
    >>> @mtime_cache
    >>> def read_file(path: Path) -> str:
    >>>     return path.read_text()
    """

    cache: dict[str, tuple[float, R]] = {}

    # find the first parameter that has a type hint that is a Path or q Union that
    # includes Path (typically `Path | str`)
    for param_idx, (param_name, param) in enumerate(
        inspect.signature(func).parameters.items()
    ):
        if (
            param.annotation is Path
            or t.get_origin(param.annotation) is t.Union
            and Path in t.get_args(param.annotation)
        ):
            break
    else:
        raise ValueError(
            f"Function {func.__name__} must have at least one parameter "
            "annotated with `pathlib.Path`."
        )

    def wrapper(*args, **kwargs) -> R:
        path = Path(kwargs.get(param_name, args[param_idx]))
        key = path.resolve(strict=False).as_posix()
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            mtime = -1
        if mtime != cache.get(key, (None,))[0]:
            cache[key] = (mtime, func(*args, **kwargs))
        return cache[key][1]

    return wrapper
