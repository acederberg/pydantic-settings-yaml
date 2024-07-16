from __future__ import annotations

import sys

from yaml_settings_pydantic import __version__


def main(*argv: str) -> int:
    if argv[1] == "version":
        print(__version__)
    else:
        print("Invalid command")
        return 1

    return 0


if __name__ == "__main__":
    status = main(*sys.argv)
    sys.exit(status)
