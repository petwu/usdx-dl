"""CLI entry point."""

import os
import sys
from pathlib import Path

from usdx_dl import ansi, cli, required_tools


def main():
    """Main function."""
    try:
        subcmd, args = cli.args.parse()

        # environment modifications
        os.environ["PATH"] = os.pathsep.join(
            [
                os.environ.get("PATH", ""),
                str(Path(sys.executable).parent),
                str(required_tools.bin_path()),
            ]
        )
        if models_dir := getattr(args, "models_dir", None):
            del args.models_dir  # type: ignore
            os.environ["TORCH_HOME"] = f"{models_dir}/torch"
            os.environ["HF_HOME"] = f"{models_dir}/hf"
            os.environ["AUDIO_SEPARATOR_MODEL_DIR"] = f"{models_dir}/separator"

        # check for missing CLI tools
        if subcmd in ["download"]:
            if missing := required_tools.missing():
                print(ansi.RED, end="", file=sys.stderr)
                print(
                    "ERROR: Please install the following required programs:",
                    file=sys.stderr,
                )
                for tool in missing:
                    print(f"  - {tool.name}: {tool.homepage}", file=sys.stderr)
                print(ansi.RESET, end="", file=sys.stderr)
                sys.exit(1)

        # run the subcommand
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
