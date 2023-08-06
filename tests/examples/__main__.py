from . import MySettings


def main() -> None:
    # Print out parsed settings as q dict/json.
    import json
    from shutil import get_terminal_size

    sep = get_terminal_size().columns * "="
    settings = MySettings()

    print(sep)
    print("Results parsed from `example.yaml`:")
    print(
        json.dumps(
            settings.model_dump(),
            default=str,
            indent=2,
        )
    )
    print(sep)


if __name__ == "__main__":
    main()
