"""Web server state management."""

from pathlib import Path
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field

from usdx_dl import __app__, models, sys_utils


class ServerConfig(BaseModel):
    """Configuration for the web server."""

    host: str = Field(frozen=True)
    port: int = Field(frozen=True)
    log_level: str = Field(frozen=True)
    tee: bool = Field(frozen=True)
    no_browser: bool = Field(frozen=True)
    unlocked_settings: bool = Field(frozen=True)
    is_webview: bool = Field(frozen=True)
    pause_processing: bool = False

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
    def data_dir(self) -> Path:
        """Path to the data directory."""
        return __app__.user_data_path / "data"

    @property
    def log_path(self) -> Path:
        """Path to the log file."""
        return self.data_dir / "server.log"

    @property
    def state_path(self) -> Path:
        """Path to the server state file."""
        return self.data_dir / "state.json"

    @property
    def setup_path(self) -> Path:
        """Path to the setup state file."""
        return self.data_dir / "setup.json"

    @property
    def ui_dir(self) -> Path:
        """Path to the user interface directory."""
        return Path(__file__).parent / "ui"

    @property
    def ui_build_dir(self) -> Path:
        """Path to the built user interface directory."""
        return Path(__file__).parent / "dist"


class ServerState(BaseModel):
    """State of the web server."""

    processing: models.PipelineContext | None = None
    queue: list[models.PipelineContext] = Field(default_factory=list)
    pending: int = 0

    def save(self) -> None:
        """Save the server state to disk."""
        path = server_cfg.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2, by_alias=False), "utf-8")

    @classmethod
    def load(cls) -> Self:
        """Load the server state from disk."""
        path = server_cfg.state_path
        try:
            return cls.model_validate_json(path.read_text("utf-8"), by_name=True)
        except:  # pylint: disable=bare-except  # noqa: E722
            return cls()


class SetupState(BaseModel):
    """State of the setup process."""

    step: int = 0
    usdb_cookie: str | None = None
    usdb_username: str | None = None

    model_config = models.config


# pylint: disable=invalid-name

server_cfg: ServerConfig
"""Global server configuration. Externally initialized."""

processing_state: ServerState
"""Global server state. Externally initialized."""

setup: SetupState
"""Global setup state. Externally initialized."""

if TYPE_CHECKING:
    server_cfg = ServerConfig  # type: ignore
    processing_state = ServerState  # type: ignore
    setup = SetupState  # type: ignore
