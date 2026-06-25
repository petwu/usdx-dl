"""Web server state management."""

import sys
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field

from usdx_dl import models


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


class ServerConfig(BaseModel):
    """Configuration for the web server."""

    host: str = Field(frozen=True)
    port: int = Field(frozen=True)
    log_level: str = Field(frozen=True)
    models_dir: Path = Field(frozen=True)
    output_dir: Path = Field(frozen=True)
    data_dir: Path = Field(frozen=True)
    tee: bool = Field(frozen=True)
    no_browser: bool = Field(frozen=True)
    unlocked_settings: bool = Field(frozen=True)

    @property
    def url(self) -> str:
        """URL of the web server."""
        return f"http://{self.host}:{self.port}/"

    @property
    def open_browser(self) -> bool:
        """Whether the web server should open the browser automatically."""
        return (
            self.ui_build_dir.exists()  #
            and not self.no_browser
            and not debugging()
        )

    @property
    def settings_path(self) -> Path:
        """Path to the settings file."""
        return self.data_dir / "settings.json"

    @property
    def log_path(self) -> Path:
        """Path to the log file."""
        return self.data_dir / "server.log"

    @property
    def state_path(self) -> Path:
        """Path to the server state file."""
        return self.data_dir / "state.json"

    @property
    def ui_build_dir(self) -> Path:
        """Path to the built user interface directory."""
        return Path(__file__).parent / "ui" / "dist"


class Settings(BaseModel):
    """Settings for a download request."""

    pin: str | None = None
    usdb_cookie: str | None = None
    stem_model: str = "demucs"
    whisper_model: str = "turbo"
    no_lyrics: bool = False
    no_video: bool = False
    pause_processing: bool = False

    model_config = models.config

    def save(self) -> None:
        """Save the server state to disk."""
        path = server_cfg.settings_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2, by_alias=False), "utf-8")

    @classmethod
    def load(cls) -> Self:
        """Load the server state from disk."""
        path = server_cfg.settings_path
        if not path.exists():
            return cls()
        return cls.model_validate_json(path.read_text("utf-8"), by_name=True)


class ServerState(BaseModel):
    """State of the web server."""

    processing: models.PipelineContext | None = None
    queue: list[models.PipelineContext] = Field(default_factory=list)

    def save(self) -> None:
        """Save the server state to disk."""
        path = server_cfg.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2, by_alias=False), "utf-8")

    @classmethod
    def load(cls) -> Self:
        """Load the server state from disk."""
        path = server_cfg.state_path
        if not path.exists():
            return cls()
        return cls.model_validate_json(path.read_text("utf-8"), by_name=True)


server_cfg: ServerConfig
"""Global server configuration. Externally initialized."""

settings: Settings
"""Global server settings. Externally initialized."""

processing_state: ServerState
"""Global server state. Externally initialized."""
