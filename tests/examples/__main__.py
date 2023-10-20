import json
import sys
from shutil import get_terminal_size
from typing import Type

from yaml_settings_pydantic import BaseYamlSettings

from . import ExplicitSettings, MinimalSettings, SubpathSettings

SEP = get_terminal_size().columns * "="


def show(config_cls: Type[BaseYamlSettings]) -> None:
    settings = config_cls()
    print(SEP)
    print("Results parsed from `example.yaml`:")
    print(
        json.dumps(
            settings.model_dump(),
            default=str,
            indent=2,
        )
    )
    print(SEP)


def main(_, *args: str) -> None:
    # Print out parsed settings as q dict/json.

    if not args or args[0] == "explicit-settings":
        show(ExplicitSettings)
        sys.exit(0)
    elif args[0] == "minimal-settings":
        show(MinimalSettings)
        sys.exit(0)
    elif args[0] == "subpath-settings":
        show(SubpathSettings)
        sys.exit(0)
    else:
        print("Invalid input.")
        sys.exit(1)


if __name__ == "__main__":
    main(*sys.argv)
