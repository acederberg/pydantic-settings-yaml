"""For non settings/configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self, Unpack

from pydantic import BaseModel

from yaml_settings_pydantic import loader


class BaseYaml(BaseModel):
    """Pydantic model loadable from yaml. See :meth:`load`."""

    _yaml_files_data: dict[Path, loader.YamlFileData]
    _yaml_files_configs: dict[Path, loader.YamlSettingsConfigDict]

    @classmethod
    def load(
        cls,
        *,
        init_kwargs: dict[str, Any] | None = None,
        yaml_exclude: dict[str, Any] | None = None,
        **yaml_settings: Unpack[loader.YamlSettingsConfigDict],
    ) -> Self:

        # if (yaml_files := yaml_settings.get("yaml_files")) is None:
        #     raise ValueError()

        yaml_files_config = loader.validate_yaml_settings_config_files(yaml_settings)
        yaml_files_data = loader.load_yaml_data(yaml_files_config)
        data = loader.validate_yaml_data(
            yaml_files_data,
            overwrite=init_kwargs,
            exclude=yaml_exclude,
        )

        return cls.model_validate(data)
