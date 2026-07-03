"""Download all necessary files (txt, cover, audio, video, etc.) for UltraStar Deluxe
and similar games that support UltraStar .txt files.

Uses AI models for these tasks:
- separation of vocals and instrumental stems (demucs or Mel-Band RoFormer)
- audio description (whisperx) [not for USDB links]
- pitch detection (swift-f0) [not for USDB links]

Getting started:
1.  Go to https://usdb.animux.de, create an account and search for songs.
2a. Copy the song URL and run:
    $ usdx-dl "https://usdb.animux.de/?link=detail&id=1368"
2b. If you can't find the song on USDB, you can also provide a YouTube link:
    $ usdx-dl "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    Note: This generates the TXT file using AI models for lyric transcription
    and pitch detection and will be less accurate.
"""

import argparse
import sys
from pathlib import Path
from typing import Callable

from usdx_dl import __version__, models


def parse() -> tuple[str | Callable, argparse.Namespace]:
    """Parse command line arguments.

    Returns:
        A tuple of:
            - The subcommand name or function to call. If it is a string, you
              will need to call the corresponding main function at
              ``usdx_dl.cli.<name>.main``.
            - The parsed arguments as a Namespace object.
    """
    cfg = models.Config.load()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    version_action = parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="cmd", title="subcommands", required=True)
    parser_cfg = subparsers.add_parser("config", help="view or edit config")
    parser_dl = subparsers.add_parser(
        "download", help="download a song (default w/ args)"
    )
    parser_ls = subparsers.add_parser("list", help="list all songs")
    parser_web = subparsers.add_parser("web", help="run the web UI")
    parser_gui = subparsers.add_parser(
        "gui", help="open the desktop app (default w/o args)"
    )
    parser_v = subparsers.add_parser("version", help=version_action.help)
    parser_cfg.set_defaults(subcmd="config")
    parser_dl.set_defaults(subcmd="download")
    parser_ls.set_defaults(subcmd="list")
    parser_web.set_defaults(subcmd="web")
    parser_gui.set_defaults(subcmd="gui")
    parser_v.set_defaults(
        subcmd=lambda: version_action(parser, argparse.Namespace(), [])
    )

    parser_cfg.add_argument(
        "key",
        type=str,
        nargs="?",
        help="Config key to view or edit. If not provided, all config keys will be"
        " printed.",
    )
    parser_cfg.add_argument(
        "value",
        type=str,
        nargs="?",
        help="New value for the config key. If not provided, the current value will "
        "be printed. Must be a valid JSON value (e.g. string, number, boolean, null, "
        "array or object).",
    )

    parser_dl.add_argument(
        "source",
        type=str,
        help="Song URL or ID from https://usdb.animux.de or https://www.youtube.com. "
        "Or path to a text file containing a list of URLs/IDs, one per line.",
    )
    parser_dl.add_argument(
        "-c",
        "--usdb-cookie",
        metavar="PHPSESSID",
        type=str,
        help="USDB login session cookie for API requests.",
    )
    for p in [parser_dl, parser_ls]:
        p.add_argument(
            "-o",
            "--output-dir",
            metavar="DIR",
            type=Path,
            default=cfg.output_dir,
            help="Output directory. (default: %(default)s)",
        )
    for p in [parser_dl, parser_web, parser_gui]:
        p.add_argument(
            "-m",
            "--models-dir",
            type=Path,
            default=cfg.models_dir,
            help="Model cache directory. (default: %(default)s)",
        )
    parser_dl.add_argument(
        "-s",
        "--stem-model",
        type=str,
        choices=["demucs", "mel-roformer"],
        default="demucs",
        help="Model used for stem separation. (default: %(default)s)",
    )
    parser_dl.add_argument(
        "-w",
        "--whisper-model",
        type=str,
        default="turbo",
        choices=["tiny", "base", "small", "medium", "large", "turbo"],
        help="Model size of the WhisperX model used for transcription. "
        "(default: %(default)s)",
    )
    parser_dl.add_argument(
        "-r",
        "--sample-rate",
        metavar="INT",
        type=int,
        default=44100,
        help="Audio sample rate. (default: %(default)s)",
    )
    parser_dl.add_argument(
        "-g",
        "--vocals-gain",
        type=float,
        metavar="0..1",
        default=0.0,
        help="Gain in [0, 1] for the vocals. Higher means vocals are louder. "
        "Use only if you use another game than UltraStart Deluxe that doesn't "
        "support setting the vocals volume within the game. "
        "(default: %(default)s)",
    )
    parser_dl.add_argument(
        "-p",
        "--phrase-correction",
        metavar="FLOAT",
        type=float,
        default=1.0,
        help="Manually correct for unintuitive phrase splits. If phrases are too "
        "short use a value >1, for too long phases a value in [0, 1). "
        "Use with `-f txt` to try various values. "
        "(default: %(default)s)",
    )
    parser_dl.add_argument(
        "-f",
        "--force",
        type=str,
        nargs="?",
        const="all",
        choices=list(models.Force),
        help="Force to rerun everything or just a specific step. "
        "Defaults to 'all' without argument.",
    )
    parser_dl.add_argument(
        "-v",
        "--no-video",
        action="store_true",
        help="Don't download the music video from YouTube and set a static "
        "background image instead.",
    )
    parser_dl.add_argument(
        "-l",
        "--no-lyrics",
        action="store_true",
        help="Don't search for synced lyrics on https://lrclib.net, instead "
        "always transcribe with WhisperX.",
    )
    parser_dl.add_argument(
        "-n",
        "--non-interactive",
        action="store_true",
        help="Enable non-interactive mode.",
    )
    parser_dl.add_argument(
        "-k",
        "--keep-going",
        action="store_true",
        help="In batch mode, keep running even if the batch file is empty and "
        "wait for new entries.",
    )

    parser_ls.add_argument(
        "-s",
        "--sort-by",
        type=str,
        choices=["id", "artist", "title"],
        default="id",
        help="Sort by artist, title or ID (directory name). (default: %(default)s)",
    )
    parser_ls.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="Inverse the sorting order.",
    )

    parser_web.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to run the web UI on. Use '0.0.0.0' or '::' to make it "
        "available on your local network. (default: %(default)s)",
    )
    parser_web.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the web UI on. (default: %(default)s)",
    )
    for p in [parser_web, parser_gui]:
        p.add_argument(
            "--log-level",
            type=str,
            choices=["debug", "info", "warning", "error", "critical"],
            default="warning",
            help="Server log level. Mostly for development/debugging. "
            "(default: %(default)s)",
        )
        p.add_argument(
            "--tee",
            action="store_true",
            help="Print logs to stdout/stderr in addition to the web UI.",
        )
        p.add_argument(
            "--unlocked-settings",
            action="store_true",
            help="Unlock the settings page in the web UI.",
        )
    parser_web.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open the web UI in default browser.",
    )

    # handle default subcommand
    argv = sys.argv[1:]
    try:
        parser.exit_on_error = False  # type: ignore
        parser.parse_known_args(argv)
        parser.exit_on_error = True  # type: ignore
    except argparse.ArgumentError as e:
        if e.argument_name == "cmd":
            # with arguments default to download
            argv.insert(0, "download")
        else:
            # without any arguments default to gui
            argv.insert(0, "gui")

    args = parser.parse_args(argv)
    subcmd = args.subcmd
    del args.cmd  # type: ignore
    del args.subcmd  # type: ignore

    return subcmd, args
