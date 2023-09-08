import logging
from os import environ, path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
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

    Changed to class decorator for better clarity of code.

    Using this properly will help you not reload the files provided.
    To disable this, set :param:``reload`` tu ``True``.

    :attr files: ``YAML`` or ``JSON`` to load.
    :attr reload: Reload when a new instance is created when ``True```.
    :attr loaded: Currently loaded content. Used to prevent reload when calling
        multiple times (see :attr:`reload`).
    :raises ValueError: When :param:``files`` has length 0.
    """

    files: Set[str]
    reload: bool
    loaded: Optional[Dict[str, Any]] = None

    def get_settings_cls_value(
        self,
        settings_cls,
        field: Literal["files", "reload"],
        default: Optional[T] = None,
    ) -> Optional[T]:
        # Bc logging
        _msg = "Looking for field `%s` as `%s` on `%s`."
        _msg_found = _msg.replace("Looking for", "Found")

        # Bc naming
        cls_field = f"__env_yaml_settings_{field}__"
        config_field = f"yaml_{field}"

        logger.debug(_msg, field, config_field, "settings_cls")
        out = default
        if (dunder := getattr(settings_cls, cls_field, None)) is not None:
            logger.debug(_msg_found, field, config_field, "settings_cls")
            return dunder

        logger.debug(_msg, field, config_field, "settings_cls.model_config")
        from_conf = settings_cls.model_config.get(config_field)
        if from_conf is not None:
            logger.debug(_msg_found, field, config_field, "settings_cls.model_config")
            return from_conf

        logger.debug("Using default value `%s` for field `%s`.", default, field)
        return out

    def __init__(
        self,
        settings_cls: Type,
    ):
        files: str | Sequence[str] | None = self.get_settings_cls_value(
            settings_cls,
            s := "files",
        )
        reload: bool | None = self.get_settings_cls_value(
            settings_cls,
            "reload",
            True,
        )

        if isinstance(files, str):
            files = [files]

        if files is None:
            raise ValueError("`files` cannot be `None`.")
        elif not len(files):
            raise ValueError("`files` cannot have length `0`.")

        logger.debug("Constructing `CreateYamlSettings`.")

        self.loaded = None
        self.reload = reload
        self.files = set(files)

    def __call__(self) -> Dict[str, Any]:
        """Yaml settings loader for a single file."""
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
        if self.loaded is None:
            raise ValueError("Must load before getting field values.")
        v = self.loaded.get(field_name)
        return (v, field_name, False)


class BaseYamlSettings(BaseSettings):
    """YAML Settings parser.

    Dunder settings will be passed to `CreateYamlSettings`s constuctor.

    :attr model_config: Secondary source for dunder (`__`) prefixed values.
    :attr __env_yaml_settings_reload__: Reload files when constructor
    :attr __env_yaml_settings_files__: All of the files to load to populate
        settings fields (in order of ascending importance).
    """

    model_config: ClassVar[YamlSettingsConfigDict]

    __env_yaml_settings_files__: ClassVar[Optional[Sequence[str]]]
    __env_yaml_settings_reload__: ClassVar[Optional[bool]]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
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
