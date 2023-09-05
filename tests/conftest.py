import logging
from os import mkdir, path, remove
from random import randint
from secrets import token_hex, token_urlsafe
from typing import Any, Dict, Generator, Optional, Tuple

import pytest
import yaml

# 705 5622

ASSETS = path.join(path.dirname(__file__), "assets")
DEFAULT_KEYS_PROB: int = 5
DEFAULT_NESTED_KEYS_PROB: int = 5
DEFAULT_MAX_DEPTH: int = 3


# Check for existance of the assets folder.
if not path.exists(ASSETS):
    logging.info(f"Creating test assets folder ``{ASSETS}``.")
    mkdir(ASSETS)
elif not path.isdir(ASSETS):
    logging.critical(f"``{ASSETS} is not a directory, but it must be.")
    raise Exception(f"``{ASSETS}`` must be a folder.")


def _create_dummy(
    keys: Tuple[str, ...],
    nested_keys: Optional[Tuple[str, ...]] = None,
    max_depth: int = DEFAULT_MAX_DEPTH,
    current_depth: int = 0,
) -> Dict[str, Any]:
    """Create a dummy data to attempt to load.

    :param keys: Keys to populate data for.
    :param nested_keys: Keys to nest at.
    :param max_depth: How far can nesting go.
    :param current_depth: Recursion depth.
    :returns: A dummy dictionary.
    """

    # Generate keys for our random dictionary.
    result = dict(((key, token_urlsafe(8)) for key in keys))

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
            )
        )

    return result


def create_dummies(
    keys: Optional[Tuple[str, ...]] = None,
    nested_keys: Optional[Tuple[str, ...]] = None,
    max_depth: Optional[int] = None,
    n_results: Optional[int] = None,
) -> Tuple[Dict[str, Any], ...]:
    """Create some dummies. For inormation on the parameters, see :func:``_create_dummy``.

    :returns: A ``tuple`` of dummies specified by the parameters.
    """

    _keys: Tuple[str, ...] = (
        keys
        if keys is not None
        else tuple(token_hex(8) for _ in range(0, randint(0, DEFAULT_KEYS_PROB)))
    )
    _nested_keys: Tuple[str, ...] = (
        nested_keys
        if nested_keys is not None
        else tuple(token_hex(8) for _ in range(0, randint(0, DEFAULT_NESTED_KEYS_PROB)))
    )
    n_results = n_results if n_results is not None else randint(1, 25)
    max_depth = max_depth if max_depth is not None else DEFAULT_MAX_DEPTH
    return tuple(
        item
        for item in (
            _create_dummy(_keys, nested_keys=_nested_keys, max_depth=max_depth)
            for _ in range(n_results)
        )
        if item is not None
    )


def write_dummies(dummies: Tuple[Dict[str, Any], ...]) -> Tuple[str, ...]:
    """Write the dummies to some files."""

    filenames = tuple(path.join(ASSETS, token_urlsafe(8)) for _ in range(len(dummies)))
    for filepath, dummy in zip(filenames, dummies):
        with open(filepath, "w") as file:
            yaml.dump(dummy, file)

    return filenames


@pytest.fixture
def fileDummies(request) -> Generator[Dict[str, Dict[str, Any]], None, None]:
    kwargs = request.params if hasattr(request, "params") else {}
    dummies = create_dummies(**kwargs)
    filenames = write_dummies(dummies)

    yield {fn: cntnt for fn, cntnt in zip(filenames, dummies)}

    kill = (remove(filename) for filename in filenames)  # type: ignore
    next(map(lambda item: item is not None, kill), None)
