"""Web server state management."""

from pathlib import Path
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field

from usdx_dl import models, sys_utils


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
            and not sys_utils.debugging()
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
    def ui_dir(self) -> Path:
        """Path to the user interface directory."""
        return Path(__file__).parent / "ui"

    @property
    def ui_build_dir(self) -> Path:
        """Path to the built user interface directory."""
        return Path(__file__).parent / "dist"


class Settings(BaseModel):
    """Settings for a download request."""

    pin: str | None = None
    usdb_cookie: str | None = None
    stem_model: str = "demucs"
    whisper_model: str = "turbo"
    no_lyrics: bool = False
    no_video: bool = False
    pause_processing: bool = False
    is_webview: bool = False

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


# pylint: disable=invalid-name

server_cfg: ServerConfig
"""Global server configuration. Externally initialized."""

settings: Settings
"""Global server settings. Externally initialized."""

processing_state: ServerState
"""Global server state. Externally initialized."""

if TYPE_CHECKING:
    server_cfg = ServerConfig  # type: ignore
    settings = Settings  # type: ignore
    processing_state = ServerState  # type: ignore
