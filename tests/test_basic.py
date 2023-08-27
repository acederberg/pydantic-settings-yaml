import pytest
import yaml
from yaml_settings_pydantic import BaseYamlSettings, CreateYamlSettings


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
