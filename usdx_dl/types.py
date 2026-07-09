from collections.abc import Callable

type ProgressCallback = Callable[[float], None]
