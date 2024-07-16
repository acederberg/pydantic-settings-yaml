from __future__ import annotations

from collections.abc import Sequence
from os import environ
from pathlib import Path
from typing import Annotated, Any, NotRequired, TypedDict

import jsonpath_ng
import yaml
from pydantic.v1.utils import deep_update
from pydantic_settings import SettingsConfigDict
from typing_extensions import Doc


class YamlFileConfigDict(TypedDict, total=False):
    # NOTE: ``NotRequired``
    envvar: NotRequired[
        Annotated[
            str | None,
            Doc(
                "Env variable for the configuration path. If this env variable "
                "is defined it will overwrite the path to which this dict is "
                "associated within ``YamlSettingsConfigDict.yaml_files`` via keys."
            ),
        ]
    ]

    subpath: NotRequired[
        Annotated[
            str | None,
            Doc("The configuration subpath of the file (using json path)."),
        ]
    ]

    required: NotRequired[
        Annotated[
            bool,
            Doc("The file specified is required."),
        ]
    ]


class YamlFileData(TypedDict):
    config: Annotated[
        YamlFileConfigDict,
        Doc("Configuration from which this data was ascertained."),
    ]
    source: Annotated[
        Path,
        Doc(
            "Origin of the content. This is here because environment "
            "variables can overwrite the source path (provided in "
            "``YamlSettingsConfigDict.files``)."
        ),
    ]
    content: Annotated[
        Any,
        Doc("Content loaded from :attr:`source`."),
    ]


DEFAULT_YAML_FILE_CONFIG_DICT = YamlFileConfigDict(
    envvar=None, subpath=None, required=True
)


class YamlSettingsConfigDict(SettingsConfigDict):
    yaml_files: Annotated[
        set[Path]
        | Sequence[Path]
        | dict[Path, YamlFileConfigDict]
        | Path
        | set[str]
        | Sequence[str]
        | dict[str, YamlFileConfigDict]
        | str,
        Doc(
            "Files to load. This can be a ``str`` or ``Sequence`` of "
            "configuration paths, or a dictionary of file names mapping to "
            "their options. This data is hydrated by ``CreateYamlSettings`` "
            "into the dictionary form ``dict[str, YamlFileConfigDict]`` no "
            "matter the form in which it is provided."
        ),
    ]

    yaml_reload: NotRequired[
        Annotated[
            bool | None,
            Doc("Reload files on object construction when ``True``."),
        ]
    ]


def resolve_filepaths(fp: Path, fp_config: YamlFileConfigDict) -> Path:

    fp_from_env = None
    if (fp_env_var := fp_config.get("envvar")) is not None:
        fp_from_env = environ.get(fp_env_var)

    fp_final = fp if not fp_from_env else Path(fp_from_env)
    return fp_final


def load_yaml_data(
    yaml_file_configs: dict[Path, YamlFileConfigDict]
) -> dict[Path, YamlFileData]:
    """Load data without validatation.

    This will transform each ``YamlFileConfigDict`` into ``YamlFileData``.
    """

    # NOTE: Check that required files exist. Find existing files and handle
    #       environment variable overwrites.
    filepaths: dict[tuple[Path, Path], YamlFileConfigDict]
    filepaths = {
        (fp_default, resolve_filepaths(fp_default, fp_config)): fp_config
        for fp_default, fp_config in yaml_file_configs.items()
    }

    # NOTE: No files to check.
    if not len(filepaths):
        return dict()

    # NOTE: If any required files are missing, raise an error.
    fp_resolved_required_missing = {
        fp_resolved
        for (_, fp_resolved), fp_config in filepaths.items()
        if fp_config.get("required") and not fp_resolved.is_file()
    }
    if len(fp_resolved_required_missing):
        raise ValueError(
            "The following files are required but do not exist: "
            f"`{fp_resolved_required_missing}`."
        )

    # NOTE: Bulk load files (and bulk manage IO closing/opening).
    # logger.debug("Loading files %s.", ", ".join(map(str, self.files)))
    files = {
        (fp_default, fp_resolved): Path.open(fp_resolved)
        for (fp_default, fp_resolved) in filepaths
        if fp_resolved.exists()
    }
    yaml_data: dict[Path, YamlFileData] = {
        fp_default: YamlFileData(
            content=yaml.safe_load(stream),
            source=fp_default,
            config=filepaths[(fp_default, fp_resolved)],
        )
        for (fp_default, fp_resolved), stream in files.items()
    }
    # logger.debug("Closing files.")
    _ = {file.close() for file in files.values()}  # type: ignore

    return yaml_data


def validate_yaml_data_content(
    fp: Path,
    fp_data: YamlFileData,
) -> tuple[dict[str, Any], Path | None]:
    """Helper of ``validate_yaml_data``.

    This will extract data from a subpath when it is specified.

    :returns: A tuple containing valid content when the second element of the
        ``tuple`` is ``None``, or invalid ...
    """

    fp_config = fp_data["config"]
    content = fp_data["content"]

    if (subpath := fp_config.get("subpath")) is not None:
        jsonpath_exp = jsonpath_ng.parse(subpath)

        extracted = next(iter(jsonpath_exp.find(content)), None)
        if extracted is None:
            msg = f"Could not find path `{subpath}` in `{fp}`."
            raise ValueError(msg)

        extracted = extracted.value
    else:
        extracted = content

    return extracted, None if isinstance(content, dict) else fp


def validate_yaml_data(
    yaml_data: dict[Path, YamlFileData],
) -> dict[str, Any]:
    """Extract subpath from loaded YAML.

    :param loaded: Loaded YAML files from :attr:`files`.
    :raises: `ValueError` when the subpaths cannot be found or when
        documents do not deserialize to dictionaries at their subpath.
    :returns: :param:`Loaded` with the subpath extracted.
    """

    if not yaml_data:
        return dict()

    # NOTE: ``dict`` is included for the case where ``loaded`` has 0 length.
    content: tuple[dict[str, Any], ...]
    fp_invalid_unfiltered: tuple[Path | None, ...]

    content, fp_invalid_unfiltered = zip(
        *(validate_yaml_data_content(fp, fp_data) for fp, fp_data in yaml_data.items()),
    )

    fp_invalid = tuple(fp for fp in fp_invalid_unfiltered if fp is not None)
    if len(fp_invalid):
        fmt = "  - `file={0}`\n`subpath={1}`"
        msg = "\n".join(
            fmt.format(fp, yaml_data[fp].get("subpath")) for fp in fp_invalid
        )
        msg = (
            "Input files must deserialize to dictionaries at their "
            f"specified subpaths:\n{msg}"
        )
        raise ValueError(msg)

    # logger.debug("Merging file results.")
    return deep_update(*content)
