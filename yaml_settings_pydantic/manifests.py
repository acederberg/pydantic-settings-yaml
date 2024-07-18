"""For non settings/configuration files.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel

from yaml_settings_pydantic import loader


class BaseYaml(BaseModel):
    """Pydantic model loadable from yaml. See :meth:`load`."""

    @classmethod
    def load(
        cls,
        *,
        overwrite: dict[str, Any] | None = None,
        exclude: dict[str, Any] | None = None,
        **yaml_settings: loader.YamlSettingsConfigDict,
    ) -> Self:

        if (yaml_files := yaml_settings.get("yaml_files")) is None:
            raise ValueError()

        yaml_files_config = loader.validate_yaml_settings_config_files(yaml_files)
        yaml_files_data = loader.load_yaml_data(yaml_files_config)
        data = loader.validate_yaml_data(
            yaml_files_data,
            overwrite=overwrite,
            exclude=exclude,
        )

        return cls.model_validate(data)
