"""Simple config file helper."""

__all__ = ["set", "get"]

import json
import os
from pathlib import Path
from typing import Any


def config_path() -> Path:
    """Path to the programs config file."""
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_dir / "usdx-dl.json"


def load() -> dict[str, Any]:
    """Load the program config."""
    config_file = config_path()
    if not config_file.exists():
        return {}
    return json.loads(config_file.read_text(encoding="utf-8"))


def save(cfg: dict[str, Any]) -> None:
    """Save the config to disk."""
    config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")


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
