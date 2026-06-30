import sys


def debugging() -> bool:
    """Check if the program is running in debug mode.

    Note:
        This function uses a heuristic based on :func:`sys.gettrace` to detect
        debug mode. It is not always accurate, but it is usually good enough.
        This function should be used rarely and only for non-critical stuff,
        as having different behavior in debug mode can be unexpected and
        confusing. It is also recommended to use this function only to set
        default values/behavior, and to provide a way to override it.

    Returns:
        bool: True if the program is running in debug mode, False otherwise.
    """
    # gettrace() is not part of the language specification, but of the CPython
    # implementation. It is not guaranteed to exist in other Python implementations.
    # Since Python 3.12, there is a new sys.monitoring module that provides an
    # event monitoring API for tools like debuggers. It provides a near-zero
    # overhead alternative to sys.gettrace(), therefore it is likely that debuggers
    # will switch to using it if possible.
    # See also https://stackoverflow.com/q/38634988.
    if sys.version_info >= (3, 12):
        # pylint: disable=no-member
        if sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID) is not None:
            return True
    return getattr(sys, "gettrace", lambda: None)() is not None
