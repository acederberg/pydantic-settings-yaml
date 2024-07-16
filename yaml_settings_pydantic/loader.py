from os import environ, path
from typing import (
    Annotated,
    Any,
    Dict,
    NotRequired,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
)

import jsonpath_ng
import yaml
from pydantic_settings import SettingsConfigDict
from typing_extensions import Doc


class YamlFileConfigDict(TypedDict):
    envvar: Annotated[
        NotRequired[Optional[str]],
        Doc(
            "Env variable for the configuration path. If this env variable "
            "is defined it will overwrite the path to which this dict is "
            "associated within ``YamlSettingsConfigDict.yaml_files`` via keys."
        ),
    ]

    subpath: Annotated[
        NotRequired[Optional[str]],
        Doc("The configuration subpath of the file (using json path)."),
    ]

    required: Annotated[
        NotRequired[bool],
        Doc("The file specified is required."),
    ]


class YamlFileData(TypedDict):
    config: Annotated[
        YamlFileConfigDict,
        Doc("Configuration from which this data was ascertained."),
    ]
    source: Annotated[
        str,
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


class YamlSettingsConfigDict(SettingsConfigDict, TypedDict):
    yaml_files: Annotated[
        Set[str] | Sequence[str] | Dict[str, YamlFileConfigDict] | str,
        Doc(
            "Files to load. This can be a ``str`` or ``Sequence`` of "
            "configuration paths, or a dictionary of file names mapping to "
            "their options. This data is hydrated by ``CreateYamlSettings`` "
            "into the dictionary form ``Dict[str, YamlFileConfigDict]`` no "
            "matter the form in which it is provided."
        ),
    ]

    yaml_reload: Annotated[
        NotRequired[Optional[bool]],
        Doc("Reload files on object construction when ``True``."),
    ]


def resolve_filepaths(fp: str, fp_config: YamlFileConfigDict) -> str:

    fp_from_env = None
    if (fp_env_var := fp_config.get("envvar")) is not None:
        fp_from_env = environ.get(fp_env_var)

    fp_final = fp if not fp_from_env else fp_from_env
    return fp_final


def load_yaml_data(
    yaml_file_configs: Dict[str, YamlFileConfigDict]
) -> Dict[str, YamlFileData]:
    """Load data without validatation.

    This will transform each ``YamlFileConfigDict`` into ``YamlFileData``.
    """

    # NOTE: Check that required files exist. Find existing files and handle
    #       environment variable overwrites.
    filepaths: Dict[Tuple[str, str], YamlFileConfigDict]
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
        if fp_config.get("required") and not path.isfile(fp_resolved)
    }
    if len(fp_resolved_required_missing):
        raise ValueError(
            "The following files are required but do not exist: "
            f"`{fp_resolved_required_missing}`."
        )

    # NOTE: Bulk load files (and bulk manage IO closing/opening).
    # logger.debug("Loading files %s.", ", ".join(self.files))
    files = {
        (fp_default, fp_resolved): open(fp_resolved)
        for (fp_default, fp_resolved) in filepaths
        if path.exists(fp_resolved)
    }
    yaml_data: Dict[str, YamlFileData] = {
        fp_default: YamlFileData(
            content=yaml.safe_load(stream),
            source=fp_default,
            config=filepaths[(fp_default, fp_resolved)],
        )
        for (fp_default, fp_resolved), stream in files.items()
    }
    # logger.debug("Closing files.")
    _ = set(file.close() for file in files.values())

    return yaml_data


def validate_yaml_data_content(
    fp: str,
    fp_data: YamlFileData,
) -> Tuple[Dict[str, Any], str | None]:
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
