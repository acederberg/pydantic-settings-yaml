import sys

from .__init__ import __version__


def main(*argv: str) -> int:
    match argv[1:]:
        case ["version"]:
            print(__version__)
        case _:
            print("Invalid command")
            return 1

    return 0


if __name__ == "__main__":
    status = main(*sys.argv)
    sys.exit(status)
