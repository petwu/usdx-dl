"""CLI entry point."""

import sys

from usdx_dl import ansi, cli


def main():
    """Main function."""
    try:
        subcmd_func, args = cli.args.parse()
        subcmd_func(**vars(args))
    except KeyboardInterrupt:
        print()
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(
            f"{ansi.RED}ERROR: {e.__class__.__name__}: {e}{ansi.RESET}", file=sys.stderr
        )
        raise e
