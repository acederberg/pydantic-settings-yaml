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

from yaml_settings_pydantic.loader import (
    DEFAULT_YAML_FILE_CONFIG_DICT,
    YamlFileConfigDict,
    YamlSettingsConfigDict,
    resolve_filepaths,
)
from yaml_settings_pydantic.manifests import BaseYaml
from yaml_settings_pydantic.settings import BaseYamlSettings, CreateYamlSettings

__version__ = "2.3.1"
__version__ = "2.3.2"


__all__ = (
    "resolve_filepaths",
    "BaseYaml",
    "BaseYamlSettings",
    "CreateYamlSettings",
    "YamlSettingsConfigDict",
    "YamlFileConfigDict",
    "DEFAULT_YAML_FILE_CONFIG_DICT",
)
