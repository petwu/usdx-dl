"""Subcommand: usdx-dl config - View or edit config."""

import sys
from typing import Any

from pydantic import TypeAdapter, ValidationError
from pydantic_core import to_json

from usdx_dl import ansi, models


def main(
    key: str | None = None,
    value: str | None = None,
):
    """Args: See :func:`.args.parse`."""
    # Load config
    try:
        cfg = models.Config.load()
    except ValidationError:
        print(f"{ansi.RED}ERROR: Invalid config file:{ansi.RESET}", file=sys.stderr)
        print(models.Config.path().read_text(), file=sys.stderr)
        print("Schema properties:", file=sys.stderr)
        for name, schema in models.Config.model_json_schema(by_alias=False)[
            "properties"
        ].items():
            print(f"- {name}: {schema}", file=sys.stderr)
        sys.exit(1)

    # check key validity
    cfg_fields = models.Config.model_fields
    valid_keys = [key for key in cfg_fields.keys()]
    if key and key not in valid_keys:
        print(
            f"{ansi.RED}ERROR: Invalid config key: {key}{ansi.RESET}", file=sys.stderr
        )
        print(f"Valid keys are:\n- {'\n- '.join(valid_keys)}", file=sys.stderr)
        sys.exit(1)

    if key is None:
        # print all config values
        for k, v in cfg.model_dump(mode="json").items():
            v = to_json(v).decode("utf-8")
            v_type: Any = cfg_fields[k].annotation  # pylint: disable=unsubscriptable-object
            if hasattr(v_type, "__name__"):
                v_type = v_type.__name__
            else:
                v_type = str(v_type)
            print(
                f"{ansi.MAGENTA}{k}{ansi.RESET} = "
                f"{ansi.CYAN}{v}{ansi.RESET} "
                f"{ansi.DIM}[{v_type}]{ansi.RESET}"
            )

    elif value is None:
        # print specific config value
        print(to_json(getattr(cfg, key)).decode("utf-8"))

    else:
        # set specific config value
        adapter: TypeAdapter = TypeAdapter(
            cfg_fields[key].annotation  # pylint: disable=unsubscriptable-object
        )
        try:
            parsed_value: Any = adapter.validate_json(value)
        except ValidationError:
            try:
                parsed_value = adapter.validate_python(value)
            except ValidationError as e:
                print(
                    f"{ansi.RED}ERROR: Invalid value for config key {key}: {value}{ansi.RESET}",
                    file=sys.stderr,
                )
                print(str(e), file=sys.stderr)
                sys.exit(1)
        setattr(cfg, key, parsed_value)
        cfg.save()
