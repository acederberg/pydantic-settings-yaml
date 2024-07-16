"""Tools for loading pydantic settings from ``YAML`` and ``JSON`` sources.

To include logging, set the environment variable
``YAML_SETTINGS_PYDANTIC_LOGGER`` to true, e.g.

.. code:: sh

    export YAML_SETTINGS_PYDANTIC_LOGGER=true

:class YamlSettingsConfigDict: Extension of ``SettingsConfigDict`` to include
    our type hints.
:class CreateYamlSettings: The ``PydanticBaseSettingsSource``.
:class BaseYamlSettings: The main class that consumers will want to use.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from os import environ
from pathlib import Path, PosixPath
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, TypeVar

from jsonpath_ng import parse
from pydantic.fields import FieldInfo
from pydantic.v1.utils import deep_update
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typing_extensions import Doc, NotRequired, TypedDict
from yaml import safe_load

__version__ = "2.3.1"
logger = logging.getLogger("yaml_settings_pydantic")
if environ.get("YAML_SETTINGS_PYDANTIC_LOGGER") == "true":
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)
T = TypeVar("T")


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


class YamlSettingsConfigDict(SettingsConfigDict, TypedDict):
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


class CreateYamlSettings(PydanticBaseSettingsSource):
    """Create a ``yaml`` setting loader middleware.


    Note that the following fields can be set using dunder ``ClassVars`` or
    ``model_config`` on ``settings_cls.model_config``.
    """

    # Info

    files: Annotated[
        dict[Path, YamlFileConfigDict],
        Doc(
            "``YAML`` or ``JSON`` files to load and loading specifications ("
            "in the form of :class:`YamlFileConfigDict`)."
        ),
    ]
    reload: Annotated[
        bool,
        Doc(
            "When ``True```, reload files specified in :param:`files` when a "
            "new instance is created. Default is `False`."
        ),
    ]

    # State
    _loaded: Annotated[
        dict[str, Any] | None,
        Doc("Loaded file(s) content."),
    ]

    # ----------------------------------------------------------------------- #
    # Top level stuff.

    def __init__(self, settings_cls: type[BaseSettings]):
        self.reload = self.validate_reload(settings_cls)
        self.files = self.validate_files(settings_cls)
        self._loaded = None

    def __call__(self) -> dict[str, Any]:
        """Yaml settings loader for a single file.

        :returns: Yaml from :attr:`files` unmarshalled and combined by update.
        """

        return self.loaded

    @property
    def loaded(self) -> dict[str, Any]:
        """Loaded file(s) content.

        Always loads content the first time. On subsequent calls, returns
        will return previously loaded content if :attr:`reload` is `False`,
        otherwise returns output by calling :meth:`load`.
        """
        if self.reload:
            logger.debug("Reloading configuration files.")
            self._loaded = self.load()
        elif self._loaded is None:
            logger.debug("Loading configuration files. Should not reload.")
            self._loaded = self.load()

        return self._loaded

    def get_field_value(
        self,
        field: FieldInfo,
        field_name: str,
    ) -> tuple[Any, str, bool]:
        """Required by pydantic."""

        v = self.loaded.get(field_name)
        return (v, field_name, False)

    # ----------------------------------------------------------------------- #
    # Field validation.

    def validate_reload(self, settings_cls: type[BaseSettings]) -> bool:
        logger.debug("`%s` validating `%s`.", self, settings_cls.__name__)
        reload: bool = self.get_settings_cls_value(
            settings_cls,
            "reload",
            True,
        )

        return reload

    def validate_files(
        self, settings_cls: type[BaseSettings]
    ) -> dict[Path, YamlFileConfigDict]:
        """Validate ``model_config["files"]``."""

        found_value: dict[Path, YamlFileConfigDict] | str | Sequence[str] | None
        found_value = self.get_settings_cls_value(settings_cls, "files", None)
        item = f"{settings_cls.__name__}.model_config.yaml_files"

        # NOTE: Validate is dict/set/Path/str
        if found_value is None:
            raise ValueError(f"`{item}` cannot be `None`.")
        elif (
            not isinstance(found_value, Path)
            and not isinstance(found_value, str)
            and not isinstance(found_value, set)
            and not isinstance(found_value, dict)
        ):
            msg = "`{0}` must be a sequence or set, got type `{1}`."
            raise ValueError(msg.format(item, type(found_value)))
        # NOTE: Not including makes the editor think the the code below is
        #       unreachable, I do not know why, so the ``else`` statement shall
        #       remain.
        else:
            ...

        # NOTE: If its a string/``Path``, make it into a tuple. If it is anything
        #       else just leave it.
        values: (
            tuple[Path, ...]
            | dict[str, YamlFileConfigDict]
            | dict[Path, YamlFileConfigDict]
        )
        if isinstance(found_value, PosixPath):
            logger.debug(f"`{item}` was a PosixPath.")
            values = (found_value,)
        elif isinstance(found_value, str):
            logger.debug(f"`{item}` was a String.")
            values = (Path(found_value),)
        else:
            values = found_value

        keys_invalid = {item for item in values if not isinstance(item, Path)}
        if len(keys_invalid):
            raise ValueError(
                "All items in `files` must be strings. The following are "
                f"not strings: `{keys_invalid}`."
            )

        # NOTE: Create dictionary if the sequence is not a dictionary.
        files: dict[Path, YamlFileConfigDict]
        if not isinstance(values, dict):
            files = {
                (
                    k if isinstance(k, Path) else Path(k)
                ): DEFAULT_YAML_FILE_CONFIG_DICT.copy()
                for k in values
            }
        elif any(not isinstance(v, dict) for v in values.values()):
            raise ValueError(f"`{item}` values must have type `dict`.")
        elif not len(values):
            raise ValueError("`files` cannot have length `0`.")
        else:
            for k, v in values.items():
                vv = DEFAULT_YAML_FILE_CONFIG_DICT.copy()
                vv.update(v)
                values[k] = v
            files = values

        return files

    def get_settings_cls_value(
        self,
        settings_cls: Any,
        field: Literal["files", "reload"],
        default: T,
    ) -> T:
        """Look for and return an attribute :param:`field` on
        :param:`settings_cls` and then :attr:`settings_cls.model_config`, if
        neither of these are found return :param:`default`.
        """
        # Bc logging
        _msg = "Looking for field `%s` as `%s` on `%s`."
        _msg_found = _msg.replace("Looking for", "Found")

        # Bc naming
        cls_field = f"__yaml_{field}__"
        config_field = f"yaml_{field}"

        # Look for dunder source
        logger.debug(_msg, f"__{field}__", config_field, "settings_cls")
        out = default
        if (dunder := getattr(settings_cls, cls_field, None)) is not None:
            logger.debug(_msg_found, field, config_field, "settings_cls")
            return dunder

        # Look for config source
        logger.debug(_msg, field, config_field, "settings_cls.model_config")
        from_conf = settings_cls.model_config.get(config_field)
        if from_conf is not None:
            logger.debug(
                _msg_found,
                field,
                config_field,
                "settings_cls.model_config",
            )
            return from_conf

        # Return defult
        logger.debug("Using default `%s` for field `%s`.", default, field)
        return out

    # ----------------------------------------------------------------------- #
    # Loading

    def validate_yaml_data_content(
        self,
        fp: Path,
        fp_data: YamlFileData,
    ) -> tuple[dict[str, Any], Path | None]:

        fp_config = fp_data["config"]
        content = fp_data["content"]

        if (subpath := fp_config.get("subpath")) is not None:
            jsonpath_exp = parse(subpath)

            extracted = next(iter(jsonpath_exp.find(content)), None)
            if extracted is None:
                msg = f"Could not find path `{subpath}` in `{fp}`."
                raise ValueError(msg)

            extracted = extracted.value
        else:
            extracted = content

        return extracted, None if isinstance(content, dict) else fp

    def validate_yaml_data(
        self,
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
            *(
                self.validate_yaml_data_content(fp, fp_data)
                for fp, fp_data in yaml_data.items()
            ),
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

        logger.debug("Merging file results.")
        return deep_update(*content)

    def load_yaml_data(self) -> dict[Path, YamlFileData]:
        """Load data without validatation."""

        # NOTE: Check that required files exist. Find existing files and handle
        #       environment variable overwrites.
        filepaths: dict[tuple[Path, Path], YamlFileConfigDict]
        filepaths = {
            (fp_default, resolve_filepaths(fp_default, fp_config)): fp_config
            for fp_default, fp_config in self.files.items()
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
                content=safe_load(stream),
                source=fp_default,
                config=filepaths[(fp_default, fp_resolved)],
            )
            for (fp_default, fp_resolved), stream in files.items()
        }
        logger.debug("Closing files.")
        _ = {file.close() for file in files.values()}  # type: ignore

        return yaml_data

    def load(self) -> dict[str, Any]:
        """Load data and validate that it is sufficiently shaped for
        ``BaseSettings``.
        """

        self._yaml_data = (yaml_data := self.load_yaml_data())
        return self.validate_yaml_data(yaml_data)


class BaseYamlSettings(BaseSettings):
    """YAML Settings.

    Dunder classvars and ``model_config`` determine how and what is loaded.

    :attr model_config: Secondary source for dunder (`__`) prefixed values.
        This should be an instance of :class:`YamlSettingsConfigDict` for
        optimal editor feedback.
    :attr __yaml_reload__: Reload files when constructor is called.
        Overwrites `model_config["yaml_reload"]`.
    :attr __yaml_files__: All of the files to load to populate
        settings fields (in order of ascending importance). Overwrites
        `model_config["yaml_reload"]`.
    """

    if TYPE_CHECKING:
        # NOTE: pydantic>=2.7 checks at load time for annotated fields, and
        #       thinks that `model_config` is a model field name.
        model_config: ClassVar[YamlSettingsConfigDict]

    __yaml_files__: ClassVar[Sequence[str] | None]
    __yaml_reload__: ClassVar[bool | None]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customizes sources for configuration. See `the pydantic docs<https://docs.pydantic.dev/latest/usage/pydantic_settings/#customise-settings-sources>`_."""

        # Look for YAML files.
        logger.debug("Creating YAML settings callable for `%s`.", cls.__name__)
        yaml_settings = CreateYamlSettings(settings_cls)

        # The order in which these appear determines their precendence. So a
        # `.env` file could be added to # override the ``YAML`` configuration
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            yaml_settings,
        )


__all__ = ("CreateYamlSettings", "YamlSettingsConfigDict", "BaseYamlSettings")
