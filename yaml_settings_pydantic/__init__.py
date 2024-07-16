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

from typing import TYPE_CHECKING, ClassVar

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from yaml_settings_pydantic import loader, util
from yaml_settings_pydantic.loader import (
    DEFAULT_YAML_FILE_CONFIG_DICT,
    YamlFileConfigDict,
    YamlSettingsConfigDict,
    resolve_filepaths,
)
from yaml_settings_pydantic.settings import CreateYamlSettings

__version__ = "2.3.1"
logger = util.get_logger(__name__)


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
        model_config: ClassVar[loader.YamlSettingsConfigDict]

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


__all__ = (
    "resolve_filepaths",
    "CreateYamlSettings",
    "BaseYamlSettings",
    "YamlSettingsConfigDict",
    "YamlFileConfigDict",
    "DEFAULT_YAML_FILE_CONFIG_DICT",
)
