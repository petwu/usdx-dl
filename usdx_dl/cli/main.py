"""CLI entry point."""

import os
import sys

from usdx_dl import ansi, cli


def main():
    """Main function."""
    try:
        subcmd, args = cli.args.parse()
        if models_dir := getattr(args, "models_dir", None):
            os.environ["TORCH_HOME"] = f"{models_dir}/torch"
            os.environ["HF_HOME"] = f"{models_dir}/hf"
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
