"""Subcommands for usdx-dl."""
# pylint: disable=redefined-builtin,import-outside-toplevel

__all__ = ["args", "config", "list", "download", "web"]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import args, config, download, list, web


# lazy import subcommands to improve startup time for all subcommands that don't need
# heavy dependencies like torch etc.
def __getattr__(name: str):
    if name in __all__:
        import importlib

        module = importlib.import_module(f"{__package__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")
