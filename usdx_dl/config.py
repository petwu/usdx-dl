"""Simple config file helper."""
# pylint: disable=redefined-builtin

__all__ = ["set", "get"]

import json
from pathlib import Path
from typing import Any

from usdx_dl import __app__


def config_path() -> Path:
    """Path to the programs config file."""
    return __app__.user_config_path / "config.json"


def load() -> dict[str, Any]:
    """Load the program config."""
    config_file = config_path()
    if not config_file.exists():
        return {}
    return json.loads(config_file.read_text(encoding="utf-8"))


def save(cfg: dict[str, Any]) -> None:
    """Save the config to disk."""
    config_file = config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def get(key: str, default: Any = None) -> Any:
    """Retrieve a value from the config."""
    cfg = load()
    return cfg.get(key, default)


def set(key: str, value: Any) -> None:
    """Set a value in the config."""
    cfg = load()
    cfg[key] = value
    save(cfg)


def unset(key: str) -> None:
    """Unset a value in the config."""
    cfg = load()
    if key in cfg:
        del cfg[key]
    save(cfg)
