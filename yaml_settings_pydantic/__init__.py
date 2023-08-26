import logging
from os import environ, path
from typing import Any, Callable, ClassVar, Dict, Optional, Tuple, Type

from pydantic.v1.utils import deep_update
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from yaml import safe_load

logger = logging.getLogger("yaml_settings_pydantic")
if environ.get("YAML_SETTINGS_PYDANTIC_LOGGER") == "true":
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)


class PydanticSettingsYamlError(Exception):
    """Error for this package."""

    ...


class CreateYamlSettings:
    """Create a ``yaml`` setting loader middleware.

    Changed to class decorator for better clarity of code.

    Using this properly will help you not reload the files provided.
    To disable this, set :param:``reload`` tu ``True``.

    :attr filepaths: ``YAML`` or ``JSON`` to load.
    :attr reload: Reload when a new instance is created when ``True```.
    :attr loaded: Currently loaded content. Used to prevent reload when calling
        multiple times (see :attr:`reload`).
    :raises ValueError: When :param:``filepaths`` has length 0.
    """

    filepaths: Tuple[str, ...]
    loaded: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        *filepaths: str,
        reload: bool = True,
    ):
        logger.debug("Constructing `CreateYamlSettings`.")
        n = len(filepaths)
        if n == 0:
            raise ValueError("Atleast one file is required.")

        self.loaded = None
        self.reload = reload
        self.filepaths = filepaths

    def __call__(
        self,
        # settings: Optional[PydanticBaseSettingsSource],
    ) -> Dict[str, Any]:
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

        :param filepaths: Paths to the `YAML` files to load and validate.
        :raises: :class:`PydanticSettingsYamlError` when any of the files do
            not deserialize to a dictionary.
        :returns: Loaded files.
        """

        # Make sure paths at least exist.
        bad = tuple(fp for fp in self.filepaths if not path.isfile(fp))
        if bad:
            raise ValueError(f"The following paths are not files: ``{bad}``.")

        # Bulk load files (and bulk manage IO closing/opening).
        logger.debug("Loading files %s.", ", ".join(self.filepaths))
        files = {filepath: open(filepath) for filepath in self.filepaths}
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
            raise PydanticSettingsYamlError(msg)

        logger.debug("Merging file results.")
        out: Dict[str, Any] = deep_update(*loaded.values())
        return out


class BaseYamlSettings(BaseSettings):
    """YAML Settings parser.

    Dunder settings will be passed to `CreateYamlSettings`s constuctor.

    :attr __env_yaml_settings_reload__: Reload files when constructor
    :attr __env_yaml_settings_files__: All of the files to load to populate
        settings fields (in order of ascending importance).
    """

    __env_yaml_settings_files__: ClassVar[Tuple[str, ...]]
    __env_yaml_settings_reload__: ClassVar[bool]

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
        files = getattr(cls, eysf := "__env_yaml_settings_files__", None)
        if files is None or not len(files):
            msg = f"`{eysf}` is required."
            raise PydanticSettingsYamlError(msg)

        yaml_settings = CreateYamlSettings(
            *files,
            reload=cls.__env_yaml_settings_reload__,
        )

        # The order in which these appear determines their precendence. So a
        # `.env` file could be added to # override the ``YAML`` configuration
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            yaml_settings,
        )


__all__ = ("CreateYamlSettings", "BaseYamlSettings")
