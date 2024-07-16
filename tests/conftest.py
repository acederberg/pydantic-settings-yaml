from __future__ import annotations

import logging
import secrets
from collections.abc import Generator
from pathlib import Path
from secrets import token_hex, token_urlsafe
from typing import Any

import pytest
import yaml

ASSETS: Path = Path(__file__).parent / "assets"
DEFAULT_KEYS_PROB: int = 5
DEFAULT_NESTED_KEYS_PROB: int = 5
DEFAULT_MAX_DEPTH: int = 3


# Check for existance of the assets folder.
if not ASSETS.exists():
    logging.info(f"Creating test assets folder ``{ASSETS}``.")
    ASSETS.mkdir(parents=True)
elif not ASSETS.is_dir():
    logging.critical(f"``{ASSETS} is not a directory, but it must be.")
    raise Exception(f"``{ASSETS}`` must be a folder.")


def _create_dummy(
    keys: tuple[str, ...],
    nested_keys: tuple[str, ...] | None = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    current_depth: int = 0,
) -> dict[str, Any]:
    """Create a dummy data to attempt to load.

    :param keys: Keys to populate data for.
    :param nested_keys: Keys to nest at.
    :param max_depth: How far can nesting go.
    :param current_depth: Recursion depth.
    :returns: A dummy dictionary.
    """

    # Generate keys for our random dictionary.
    result = {key: token_urlsafe(8) for key in keys}

    # Check recursion limit.
    if nested_keys is not None and -1 < current_depth < max_depth:
        result.update(
            iter(
                (
                    key,
                    _create_dummy(
                        keys,
                        nested_keys=nested_keys,
                        max_depth=max_depth,
                        current_depth=current_depth + 1,
                    ),
                )
                for key in nested_keys
            ),  # type: ignore
        )

    return result


def create_dummies(
    keys: tuple[str, ...] | None = None,
    nested_keys: tuple[str, ...] | None = None,
    max_depth: int | None = None,
    n_results: int | None = None,
) -> tuple[dict[str, Any], ...]:
    """Create some dummies. For inormation on the parameters, see :func:``_create_dummy``.

    :returns: A ``tuple`` of dummies specified by the parameters.
    """

    _keys: tuple[str, ...] = (
        keys if keys is not None else tuple(token_hex(8) for _ in range(0, secrets.randbelow(DEFAULT_KEYS_PROB)))
    )
    _nested_keys: tuple[str, ...] = (
        nested_keys
        if nested_keys is not None
        else tuple(token_hex(8) for _ in range(0, secrets.randbelow(DEFAULT_NESTED_KEYS_PROB)))
    )
    n_results = n_results if n_results is not None else secrets.choice(range(1, 26))
    max_depth = max_depth if max_depth is not None else DEFAULT_MAX_DEPTH
    return tuple(
        item
        for item in (_create_dummy(_keys, nested_keys=_nested_keys, max_depth=max_depth) for _ in range(n_results))
        if item is not None
    )


def write_dummies(dummies: tuple[dict[str, Any], ...]) -> tuple[Path, ...]:
    """Write the dummies to some files."""

    filenames = tuple(ASSETS / token_urlsafe(8) for _ in range(len(dummies)))
    for filepath, dummy in zip(filenames, dummies):
        with filepath.open("w") as file:
            yaml.dump(dummy, file)

    return filenames


@pytest.fixture
def file_dummies(request: Any) -> Generator[dict[Path, dict[str, Any]], None, None]:
    kwargs = request.params if hasattr(request, "params") else {}
    dummies = create_dummies(**kwargs)
    filenames = write_dummies(dummies)

    yield dict(zip(filenames, dummies))

    kill = (Path(filename).unlink() for filename in filenames)  # type: ignore
    next((item is not None for item in kill), None)
