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
import logging
from os import environ, path
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from jsonpath_ng import parse
from pydantic.fields import FieldInfo
from pydantic.v1.utils import deep_update
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typing_extensions import NotRequired, Self, TypedDict
from yaml import safe_load

__version__ = "2.0.1"
logger = logging.getLogger("yaml_settings_pydantic")
if environ.get("YAML_SETTINGS_PYDANTIC_LOGGER") == "true":
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)

T = TypeVar("T")


class YamlFileConfigDict(TypedDict):
    subpath: Optional[str]
    required: bool


DEFAULT_YAML_FILE_CONFIG_DICT = YamlFileConfigDict(subpath=None, required=True)


class YamlSettingsConfigDict(SettingsConfigDict, TypedDict):
    yaml_files: Set[str] | Sequence[str] | Dict[str, YamlFileConfigDict] | str
    yaml_reload: NotRequired[Optional[bool]]


class CreateYamlSettings(PydanticBaseSettingsSource):
    """Create a ``yaml`` setting loader middleware.

    Note that the following fields can be set using dunder ``ClassVars`` or
    ``model_config`` on ``settings_cls.model_config``.

    :attr files: ``YAML`` or ``JSON`` files to load and loading specifications
        (in the form of :class:`YamlFileConfigDict`).
    :attr reload:  When ``True```, reload files specified in :param:`files`
        when a new instance is created. Default is `False`.
    :attr loaded: Loaded file(s) content.
    """

    # Info
    files: Dict[str, YamlFileConfigDict]
    reload: bool

    # State
    _loaded: Optional[Dict[str, Any]] = None

    # ----------------------------------------------------------------------- #
    # Top level stuff.

    def __init__(self, settings_cls: Type[BaseSettings]):
        self.reload = self.validate_reload(settings_cls)
        self.files = self.validate_files(settings_cls)

    def __call__(self) -> Dict[str, Any]:
        """Yaml settings loader for a single file.
        :returns: Yaml from :attr:`files` unmarshalled and combined by update.
        """

        return self.loaded

    @property
    def loaded(self) -> Dict[str, Any]:
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
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """Required by pydantic."""

        v = self.loaded.get(field_name)
        return (v, field_name, False)

    # ----------------------------------------------------------------------- #
    # Field validation.

    def validate_reload(self, settings_cls: Type[BaseSettings]) -> bool:
        logger.debug("`%s` validating `%s`.", self, settings_cls.__name__)
        reload: bool = self.get_settings_cls_value(
            settings_cls,
            "reload",
            True,
        )

        return reload

    def validate_files(
        self, settings_cls: Type[BaseSettings]
    ) -> Dict[str, YamlFileConfigDict]:
        value: Dict[str, YamlFileConfigDict] | str | Sequence[str] | None
        value = self.get_settings_cls_value(settings_cls, "files", None)
        item = f"{settings_cls.__name__}.model_config.yaml_files"

        # Validate is sequence, not none
        if value is None:
            raise ValueError(f"`{item}` cannot be `None`.")
        elif (
            not isinstance(value, Sequence)
            and not isinstance(value, set)
            and not isinstance(value, dict)
        ):
            msg = "`{0}` must be a sequence or set, got type `{1}`."
            raise ValueError(msg.format(item, type(value)))

        # If its a string, make it into a tuple.
        # This will become a dict in the next step.
        if isinstance(value, str):
            logger.debug(f"`{item}` was a string.")
            value = (value,)

        if any(not isinstance(item, str) for item in value):
            raise ValueError("All items in `files` must be strings.")

        # Create dictionary if the sequence is not a dictionary.
        files: Dict[str, YamlFileConfigDict]
        if not isinstance(value, dict):
            files = {k: DEFAULT_YAML_FILE_CONFIG_DICT.copy() for k in value}
        elif any(not isinstance(v, dict) for v in value.values()):
            raise ValueError(f"`{item}` values must have type `dict`.")
        elif not len(value):
            raise ValueError("`files` cannot have length `0`.")
        else:
            for k, v in value.items():
                vv = DEFAULT_YAML_FILE_CONFIG_DICT.copy()
                vv.update(v)
                value[k] = v
            files = value

        return files

    def get_settings_cls_value(
        self,
        settings_cls,
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

    def _validate_loaded(
        self,
        filename,
        filecontent: Any,
        bad: List[str],
    ) -> Any:
        subpath = self.files[filename]["subpath"]
        if subpath is not None:
            jsonpath_exp = parse(subpath)
            filecontent = next(iter(jsonpath_exp.find(filecontent)), None)
            if filecontent is None:
                msg = f"Could not find path `{subpath}` in `{filename}`."
                raise ValueError(msg)
            filecontent = filecontent.value

        if not isinstance(filecontent, dict):
            bad.append(filename)

        return filecontent

    def validate_loaded(self, loaded: Dict[str, Any]) -> Dict[str, Dict]:
        """Extract subpath from loaded YAML.

        :param loaded: Loaded YAML files from :attr:`files`.
        :raises: `ValueError` when the subpaths cannot be found or when
            documents do not deserialize to dictionaries at their subpath.
        :returns: :param:`Loaded` with the subpath extracted.
        """
        # Bulk validate. This will extract data from subpaths.
        bad_files: List[str] = list()
        loaded = {
            filepath: self._validate_loaded(filepath, filecontent, bad_files)
            for filepath, filecontent in loaded.items()
        }
        if bad_files:
            fmt = "  - `file={0}`\n`subpath={1}`"
            msg = "\n".join(
                fmt.format(bad_file, self.files[bad_file]["subpath"])
                for bad_file in bad_files
            )
            msg = (
                "Input files must deserialize to dictionaries at their "
                f"specified subpaths:\n{msg}"
            )
            raise ValueError(msg)

        logger.debug("Merging file results.")
        out: Dict[str, Any] = deep_update(*loaded.values())
        return out

    def load(self) -> Dict[str, Any]:
        """Load data and validate that it is sufficiently shaped for
        ``BaseSettings``.

        :param files: Paths to the `YAML` files to load and validate.
        :raises: :class:`ValueError` when any of the files do not exist but
            they are required.
        :returns: Loaded files.
        """

        # Check that required files exist. Find existing files.
        required = set(fp for fp in self.files if self.files[fp]["required"])
        existing = set(fp for fp in self.files if path.isfile(fp))

        # If any required files are missing, raise an error.
        if len(bad := required - existing):
            raise ValueError(
                f"The following files are required but do not exist: `{bad}`."
            )

        # No required files are missing, and none exist.
        elif not (existing):
            return dict()

        # Bulk load files (and bulk manage IO closing/opening).
        logger.debug("Loading files %s.", ", ".join(self.files))
        files = {filepath: open(filepath) for filepath in existing}
        loaded_raw: Dict[str, Any] = {
            filepath: safe_load(file) for filepath, file in files.items()
        }
        logger.debug("Closing files.")
        _ = set(file.close() for file in files.values())

        return self.validate_loaded(loaded_raw)


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

    model_config: ClassVar[YamlSettingsConfigDict]
    __yaml_files__: ClassVar[Optional[Sequence[str]]]
    __yaml_reload__: ClassVar[Optional[bool]]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """Customizes sources for configuration. See `the pydantic docs<https://docs.pydantic.dev/latest/usage/pydantic_settings/#customise-settings-sources>`."""

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
