"""CLI entry point."""

import os
import shutil
import sys

from usdx_dl import ansi, cli

REQUIRED_PROGRAMS = {
    "ffmpeg": "https://ffmpeg.org",
    "yt-dlp": "https://github.com/yt-dlp/yt-dlp",
}


def main():
    """Main function."""
    try:
        subcmd, args = cli.args.parse()

        if models_dir := getattr(args, "models_dir", None):
            os.environ["TORCH_HOME"] = f"{models_dir}/torch"
            os.environ["HF_HOME"] = f"{models_dir}/hf"

        if subcmd in ["download", "web"]:
            missing = [name for name in REQUIRED_PROGRAMS if not shutil.which(name)]
            if missing:
                print(
                    f"{ansi.RED}ERROR: Please install the following required programs:",
                    file=sys.stderr,
                )
                for name in missing:
                    print(f"  - {name}: {REQUIRED_PROGRAMS[name]}", file=sys.stderr)
                print(ansi.RESET)
                sys.exit(1)

        if callable(subcmd):
            subcmd(**vars(args))
        else:
            assert isinstance(subcmd, str)
            getattr(cli, subcmd).main(**vars(args))

    except KeyboardInterrupt:
        print()
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"{ansi.RED}ERROR: {e.__class__.__name__}: {e}{ansi.RESET}", file=sys.stderr
        )
        raise e
