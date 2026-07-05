"""Subcommand: usdx-dl web - Run the web UI."""

import subprocess
import threading

import uvicorn

from usdx_dl import ansi, sys_utils, web

__all__ = ["main"]


def main(**kwargs) -> None:
    """Args: See :func:`.args.parse`."""
    ansi.force_color()

    # initialize the web server
    cfg, app = web.init_server(**kwargs)
    web.print_server_info(cfg)

    # for convenience, start the vite dev server if debugging
    if sys_utils.debugging():
        print(f"{ansi.BOLD}Starting vite dev server ...{ansi.RESET}")
        threading.Thread(
            target=subprocess.run,
            args=(["pnpm", "run", "dev"],),
            kwargs={"cwd": cfg.ui_dir, "check": True},
        ).start()

    # start the web server
    uvicorn.run(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level=cfg.log_level,
    )
