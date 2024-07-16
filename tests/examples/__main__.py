from __future__ import annotations

import json
from shutil import get_terminal_size

import click

from yaml_settings_pydantic import BaseYamlSettings

from . import ExplicitSettings, MinimalSettings, SubpathSettings

SEP = get_terminal_size().columns * "="


def show(config_cls: type[BaseYamlSettings]) -> None:
    settings = config_cls()
    print(SEP)
    print("Results parsed from `example.yaml`:")
    print(
        json.dumps(
            settings.model_dump(),
            default=str,
            indent=2,
        ),
    )
    print(SEP)


@click.command()
def explicit_settings() -> None:
    show(ExplicitSettings)


@click.command()
def minimal_settings() -> None:
    show(MinimalSettings)


@click.command()
def subpath_settings() -> None:
    show(SubpathSettings)


@click.group()
def main() -> None:
    pass


main.add_command(explicit_settings)
main.add_command(minimal_settings)
main.add_command(subpath_settings)


if __name__ == "__main__":
    main()
