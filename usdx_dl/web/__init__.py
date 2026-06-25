"""Web UI for usdx-dl."""

import asyncio
import socket
import webbrowser
from contextlib import asynccontextmanager
from threading import Thread

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from usdx_dl import ansi
from usdx_dl.interactive import CliPrompt
from usdx_dl.web import api, state, worker, ws


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


def main(**kwargs) -> None:
    """Args: See :func:`..cli.args.parse`."""
    # initialize the server config, settings and state
    state.server_cfg = state.ServerConfig(**kwargs)
    state.server_cfg.log_path.parent.mkdir(parents=True, exist_ok=True)
    state.server_cfg.log_path.write_text("", encoding="utf-8")
    if state.server_cfg.settings_path.exists():
        state.settings = state.Settings.load()
    else:
        state.settings = state.Settings()
    if not state.server_cfg.unlocked_settings and state.settings.pin is None:
        hint = CliPrompt.string(
            "Set a numeric PIN for the settings page (leave blank to disable)",
        ).strip()
        if hint != "" and not hint.isdigit():
            raise ValueError("PIN must be numeric.")
        state.settings.pin = hint
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

    # print startup messages
    print(f"Web UI running at: {ansi.CYAN}{state.server_cfg.url}{ansi.RESET}")
    if state.server_cfg.host == "0.0.0.0":
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        lan_url = f"http://{ip}:{state.server_cfg.port}/"
        print(f"LAN-accessible at: {ansi.CYAN}{lan_url}{ansi.RESET}")
    if not state.server_cfg.unlocked_settings and state.settings.pin:
        hint = "*" * len(state.settings.pin)
        print(f"{ansi.DIM}Settings page is protected by a PIN ({hint}).{ansi.RESET}")

    # start the server
    uvicorn.run(
        app,
        host=state.server_cfg.host,
        port=state.server_cfg.port,
        log_level=state.server_cfg.log_level,
    )
