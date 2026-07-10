"""Web UI for usdx-dl."""

import asyncio
import socket
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from usdx_dl import ansi, models, required_tools
from usdx_dl.web import api, assets, state, worker, ws
from usdx_dl.web.state import ServerConfig

__all__ = ["init_server", "ServerConfig"]


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=unused-argument
    """Start the worker thread when the app starts, and stop it when the app stops."""
    loop = asyncio.get_event_loop()
    cfg = models.Config.load()
    with ws.capture_output(
        loop,
        log_path=state.server_cfg.log_path,
        tee=state.server_cfg.tee,
    ):
        # start worker thread
        worker.start()

        # open browser if requested
        if state.server_cfg.open_browser:
            loop.call_soon(
                lambda: webbrowser.open(state.server_cfg.url, new=2, autoraise=True)
            )

        # set up file system watchers that push updates to the web UI when files change
        fs_observers = [
            ws.fs_watch(loop, "state", state.server_cfg.state_path, api.get_state, 0.1),
            ws.fs_watch(loop, "settings", cfg.path(), api.get_settings, 0.1),
            ws.fs_watch(loop, "songs", cfg.output_dir, api.get_songs, 1.0),
            ws.fs_watch(loop, "tools", required_tools.bin_path(), api.get_tools, 1.0),
        ]

        yield

        # stop all background threads
        for o in fs_observers:
            o.stop()
            o.join(timeout=1)
        worker.stop()


def init_server(**kwargs) -> tuple[ServerConfig, FastAPI]:
    """Args: See :func:`..cli.args.parse`."""
    # initialize the server config and state
    is_webview = kwargs.pop("webview", False)
    if is_webview:
        kwargs["no_browser"] = True
    state.server_cfg = ServerConfig(**kwargs, is_webview=is_webview)
    state.server_cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    state.server_cfg.log_path.write_text("", encoding="utf-8")
    state.processing_state = state.ServerState.load()
    state.processing_state.pending = 0
    state.processing_state.save()

    # instantiate the server and mount the routes
    app = FastAPI(lifespan=lifespan)
    app.include_router(api.router)
    app.include_router(ws.router)
    app.include_router(assets.router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if state.server_cfg.ui_build_dir.exists():
        app.mount("/", StaticFiles(directory=state.server_cfg.ui_build_dir, html=True))

    return state.server_cfg, app


def print_server_info(server_cfg: ServerConfig) -> None:
    """Print server startup messages to the console."""
    cfg = models.Config.load()
    print(f"Web UI running at: {ansi.CYAN}{server_cfg.url}{ansi.RESET}")
    if server_cfg.host == "0.0.0.0":
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        lan_url = f"http://{ip}:{server_cfg.port}/"
        print(f"LAN-accessible at: {ansi.CYAN}{lan_url}{ansi.RESET}")
    if not server_cfg.unlocked_settings and cfg.pin:
        hint = "*" * len(cfg.pin)
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
