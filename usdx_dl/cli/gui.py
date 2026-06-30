"""Subcommand: usdx-dl gui - Open the desktop app."""

import socket
import subprocess
import threading
import time

import uvicorn
import webview

from usdx_dl import __app_name__, platform_utils, sys_utils, web


def main(**kwargs) -> None:
    """Args: See :func:`.args.parse`."""
    # find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        host, port = s.getsockname()

    # start the server
    cfg, app = web.init_server(
        host=host,
        port=port,
        webview=True,
        **kwargs,
    )
    if sys_utils.debugging():
        subprocess.run(["npm", "run", "build"], cwd=cfg.ui_dir, check=True)
    t = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={
            "host": host,
            "port": port,
            "log_level": cfg.log_level,
        },
    )
    t.daemon = True
    t.start()

    # open the webview window
    while not web.is_server_running(cfg.host, cfg.port):
        time.sleep(0.1)
    webview.create_window(
        title=__app_name__,
        url=cfg.url,
        width=440,
        height=720,
        min_size=(400, 240),
        background_color="#1e1e1e" if platform_utils.is_dark_mode() else "#f5f5f5",
        text_select=False,
    )
    webview.start(
        icon=(cfg.ui_dir / "assets" / "logo.svg").as_posix(),
        ssl=True,
    )
