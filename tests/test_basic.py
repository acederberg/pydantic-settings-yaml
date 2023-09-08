from typing import Set, Tuple

import pytest
import yaml
from yaml_settings_pydantic import (
    BaseYamlSettings,
    CreateYamlSettings,
    YamlSettingsConfigDict,
)


class TestCreateYamlSettings:
    def test_reload(self, fileDummies):
        # Test args
        with pytest.raises(ValueError):
            CreateYamlSettings(BaseYamlSettings)

        # Make sure it works. Check name of returned learcal
        def create_settings(reload=None, files=None):
            return type(
                "Settings",
                (BaseYamlSettings,),
                dict(
                    __env_yaml_settings_reload__=reload or False,
                    __env_yaml_settings_files__=files or set(fileDummies),
                ),
            )

        Settings = create_settings()
        yaml_settings = CreateYamlSettings(Settings)
        yaml_settings()
        assert not yaml_settings.reload

        # Malform a file.
        bad = Settings.__env_yaml_settings_files__.pop()
        with open(bad, "w") as file:
            yaml.dump([], file)

        # Loading should not be an error as the files should not be reloaded.
        yaml_settings()

        # Test reloading with bad file.
        # This could be called without the args as mutation is visible to fn
        Settings = create_settings()
        yaml_settings = CreateYamlSettings(Settings)

        with pytest.raises(ValueError) as err:
            yaml_settings()

        assert str(bad) in str(err.value)

        with open(bad, "w") as file:
            yaml.dump({}, file)

        yaml_settings()

    def test_dunders_have_priority(self) -> None:
        init_files: Set[str] = {"foo-bar.yaml"}
        model_config = YamlSettingsConfigDict(
            yaml_reload=(init_reload := True),
            yaml_files=init_files,
        )

        Settings = type(
            "Settings",
            (BaseYamlSettings,),
            dict(model_config=model_config),
        )
        yaml_settings = CreateYamlSettings(Settings)

        assert yaml_settings.files == init_files
        assert yaml_settings.reload == init_reload

        final_files: Set[str] = {"spam-eggs.yaml"}
        OverwriteSettings = type(
            "OverwriteSettings",
            (Settings,),
            dict(__env_yaml_settings_files__=final_files),
        )
        yaml_settings = CreateYamlSettings(OverwriteSettings)

        assert yaml_settings.files == final_files
        assert yaml_settings.reload == init_reload
