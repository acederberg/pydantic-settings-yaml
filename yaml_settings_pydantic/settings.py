from pathlib import Path
from typing import Annotated, Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from typing_extensions import Doc

from yaml_settings_pydantic import loader, util

logger = util.get_logger(__name__)


class CreateYamlSettings(PydanticBaseSettingsSource):
    """Create a ``yaml`` setting loader middleware.


    Note that the following fields can be set using dunder ``ClassVars`` or
    ``model_config`` on ``settings_cls.model_config``.
    """

    yaml_reload: Annotated[
        bool,
        Doc(
            "When ``True```, reload files specified in :param:`files` when a "
            "new instance is created. Default is `False`."
        ),
    ]
    yaml_files_configs: Annotated[
        dict[Path, loader.YamlFileConfigDict],
        Doc(
            "``YAML`` or ``JSON`` files to load and loading specifications ("
            "in the form of :class:`YamlFileConfigDict`)."
        ),
    ]
    yaml_files_data: Annotated[
        dict[Path, loader.YamlFileData],
        Doc("Hydrated data of ``yaml_file_configs``."),
    ]

    _loaded: Annotated[
        dict[str, Any] | None,
        Doc("Loaded file(s) content."),
    ]

    # ----------------------------------------------------------------------- #
    # Top level stuff.

    def __init__(self, settings_cls: type[BaseSettings], *, load: bool = True):
        self.settings_cls = settings_cls

        conf: loader.YamlSettingsConfigDict
        conf = settings_cls.model_config  # type: ignore

        yaml_files = loader.validate_yaml_settings_config_files(conf)
        yaml_reload = loader.validate_yaml_settings_config_reload(conf)

        # if (yaml_files_configs := settings_cls.model_config.get("yaml_files")) is None:
        #     raise ValueError("Missing ``model_config['yaml_files_configs']``.")

        self.yaml_files_configs = yaml_files
        self.yaml_reload = yaml_reload
        self._loaded = None
        if load:
            self.load()

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
        if self.yaml_reload:
            logger.debug("Reloading configuration files.")
            self._loaded = self.load()
        elif self._loaded is None:
            logger.debug("Loading configuration files. Should not reload.")
            self._loaded = self.load()

        return self._loaded

    def load(self) -> dict[str, Any]:
        """Load data and validate that it is sufficiently shaped for
        ``BaseSettings``.
        """

        self.yaml_files_data = loader.load_yaml_data(self.yaml_files_configs)
        return loader.validate_yaml_data(self.yaml_files_data)

    def get_field_value(
        self,
        field: FieldInfo,
        field_name: str,
    ) -> tuple[Any, str, bool]:
        """Required by pydantic."""

        v = self.loaded.get(field_name)
        return (v, field_name, False)
