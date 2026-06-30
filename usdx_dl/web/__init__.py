"""Web UI for usdx-dl."""

import asyncio
import socket
import webbrowser
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from usdx_dl import ansi, models
from usdx_dl.interactive import CliPrompt
from usdx_dl.web import api, state, worker, ws
from usdx_dl.web.state import ServerConfig

__all__ = ["init_server", "ServerConfig"]


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=unused-argument
    """Start the worker thread when the app starts, and stop it when the app stops."""
    loop = asyncio.get_event_loop()
    with ws.capture_output(
        loop,
        log_path=state.server_cfg.log_path,
        tee=state.server_cfg.tee,
    ):
        worker_thread = Thread(target=worker.loop, daemon=True)
        worker_thread.start()

        if state.server_cfg.open_browser:
            loop.call_soon(
                lambda: webbrowser.open(state.server_cfg.url, new=2, autoraise=True)
            )

        yield

        worker.stop_event.set()
        worker_thread.join(timeout=3)


def init_server(**kwargs) -> tuple[ServerConfig, FastAPI]:
    """Args: See :func:`..cli.args.parse`."""
    # initialize the server config, settings and state
    is_webview = kwargs.pop("webview", False)
    if is_webview:
        kwargs["no_browser"] = True
    state.server_cfg = ServerConfig(**kwargs)
    state.server_cfg.output_dir.mkdir(parents=True, exist_ok=True)
    state.server_cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    state.server_cfg.log_path.write_text("", encoding="utf-8")
    if state.server_cfg.settings_path.exists():
        state.settings = state.Settings.load()
    else:
        state.settings = state.Settings()
    state.settings.is_webview = is_webview
    if not state.server_cfg.unlocked_settings and state.settings.pin is None:
        hint = CliPrompt.string(
            "Set a numeric PIN for the settings page (leave blank to disable)",
        ).strip()
        if hint != "" and not hint.isdigit():
            raise ValueError("PIN must be numeric.")
        state.settings.pin = hint
    cfg = models.Config.load()
    state.settings.usdb_cookie = cfg.usdb_cookie or state.settings.usdb_cookie
    state.settings.save()
    state.processing_state = state.ServerState.load()

    # instantiate the server and mount the routes
    app = FastAPI(lifespan=lifespan)
    app.include_router(api.router)
    app.include_router(ws.router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/songs", StaticFiles(directory=state.server_cfg.output_dir))
    if state.server_cfg.ui_build_dir.exists():
        app.mount("/", StaticFiles(directory=state.server_cfg.ui_build_dir, html=True))

    return state.server_cfg, app


def print_server_info(cfg: ServerConfig) -> None:
    """Print server startup messages to the console."""
    print(f"Web UI running at: {ansi.CYAN}{cfg.url}{ansi.RESET}")
    if cfg.host == "0.0.0.0":
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        lan_url = f"http://{ip}:{cfg.port}/"
        print(f"LAN-accessible at: {ansi.CYAN}{lan_url}{ansi.RESET}")
    if not cfg.unlocked_settings and state.settings.pin:
        hint = "*" * len(state.settings.pin)
        print(f"{ansi.DIM}Settings page is protected by a PIN ({hint}).{ansi.RESET}")


def is_server_running(host: str, port: int) -> bool:
    """Check if the server is already running on the given host and port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.5)
            s.connect((host, port))
            return True
        except (ConnectionRefusedError, OSError):
            return False
