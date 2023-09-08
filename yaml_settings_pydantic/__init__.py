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
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from pydantic.fields import FieldInfo
from pydantic.v1.utils import deep_update
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from yaml import safe_load

logger = logging.getLogger("yaml_settings_pydantic")
if environ.get("YAML_SETTINGS_PYDANTIC_LOGGER") == "true":
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)


class YamlSettingsConfigDict(SettingsConfigDict):
    yaml_files: Set[str]
    yaml_reload: bool


T = TypeVar("T")


class CreateYamlSettings(PydanticBaseSettingsSource):
    """Create a ``yaml`` setting loader middleware.

    Using this properly will help you not reload files unecessarily.
    To disable this, set :param:``reload`` to ``True``.

    :attr files: ``YAML`` or ``JSON`` files to load.
    :attr reload: Reload when a new instance is created when ``True```. Default
        is false. Not required as a 'dunder' or in
        ``settings_cls.model_config``.
    :attr loaded: Loaded files content. Used to prevent reload when calling
        multiple times (see :attr:`reload`). required as a 'dunder' or in
        ``settings_cls.model_config``. This can be useful when debugging your
        settings in development mode where reloading might be useful on
        application reloads (e.g. if a tool uvicorn reload doesn't reload the
        configuration already).
    :raises ValueError: When :param:``files`` has length 0.
    """

    files: Set[str]
    reload: bool
    loaded: Optional[Dict[str, Any]] = None

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
        logger.debug(_msg, field, config_field, "settings_cls")
        out = default
        if (dunder := getattr(settings_cls, cls_field, None)) is not None:
            logger.debug(_msg_found, field, config_field, "settings_cls")
            return dunder

        # Look for config source
        logger.debug(_msg, field, config_field, "settings_cls.model_config")
        from_conf = settings_cls.model_config.get(config_field)
        if from_conf is not None:
            logger.debug(_msg_found, field, config_field, "settings_cls.model_config")
            return from_conf

        # Return defult
        logger.debug("Using default `%s` for field `%s`.", default, field)
        return out

    def __init__(
        self,
        settings_cls: Type,
    ):
        # Validation of `reload`.
        logger.debug("`%s` validating `%s`.", self, settings_cls.__name__)
        reload: bool = self.get_settings_cls_value(settings_cls, "reload", True)

        # Validation of files.
        files: str | Sequence[str] | None
        files = self.get_settings_cls_value(settings_cls, "files", None)
        if isinstance(files, str):
            logger.debug("`files` was a string.")
            files = [files]
        if files is None:
            raise ValueError("`files` cannot be `None`.")
        elif not len(files):
            raise ValueError("`files` cannot have length `0`.")

        # Assignment
        logger.debug("Constructing `CreateYamlSettings`.")
        self.loaded = None
        self.reload = reload
        self.files = set(files)

    def __call__(self) -> Dict[str, Any]:
        """Yaml settings loader for a single file.

        This works because it is called at some point. Returns previously
        loaded content if :attr:`reload` is `True` otherwise returns output
        from :meth:`load`.

        :returns: Yaml from :attr:`files` unmarshalled and combined by update.
        """
        if self.reload:
            logger.debug("Reloading configuration files.")
            self.loaded = self.load()
        elif self.loaded is None:
            logger.debug("Loading configuration files. Should not reload.")
            self.loaded = self.load()

        return self.loaded

    def load(self) -> Dict[str, Any]:
        """Load data and validate that it is sufficiently shaped for
        ``BaseSettings``.

        :param files: Paths to the `YAML` files to load and validate.
        :raises: :class:`ValueError` when any of the files do
            not deserialize to a dictionary.
        :returns: Loaded files.
        """

        # Make sure paths at least exist.
        bad = tuple(fp for fp in self.files if not path.isfile(fp))
        if bad:
            raise ValueError(f"The following paths are not files: ``{bad}``.")

        # Bulk load files (and bulk manage IO closing/opening).
        logger.debug("Loading files %s.", ", ".join(self.files))
        files = {filepath: open(filepath) for filepath in self.files}
        loaded: Dict[str, Dict] = {
            filepath: safe_load(file) for filepath, file in files.items()
        }
        logger.debug("Closing files.")
        for file in files.values():
            file.close()

        # Bulk validate. Settings requires key value pairs.
        if bad := tuple(
            filepath
            for filepath, filecontent in loaded.items()
            if not isinstance(filecontent, dict)
        ):
            msg = "Input files must deserialize to dictionaries:\n"
            logger.critical(msg := msg + "\n".join(f"  - {b}" for b in bad))
            raise ValueError(msg)

        logger.debug("Merging file results.")
        out: Dict[str, Any] = deep_update(*loaded.values())
        return out

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        # Method required by the metaclass. It worked without this somehow.
        if self.loaded is None:
            raise ValueError("Must load before getting field values.")
        v = self.loaded.get(field_name)
        return (v, field_name, False)


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
        """Customizes sources for configuration. See https://docs.pydantic.dev/latest/usage/pydantic_settings/#customise-settings-sources."""

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
