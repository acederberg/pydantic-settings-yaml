import pytest
import yaml
from yaml_settings_pydantic import (
    BaseYamlSettings,
    CreateYamlSettings,
    PydanticSettingsYamlError,
)


class TestCreateYamlSettings:
    def test_reload(self, fileDummies):
        # Test args
        with pytest.raises(ValueError):
            CreateYamlSettings()

        # Make sure it works. Check name of returned local
        filenames = set(fileDummies.keys())
        yaml_settings = CreateYamlSettings(*fileDummies, reload=False)
        yaml_settings()
        assert "reload" not in str(yaml_settings)

        # Malform a file.
        bad = filenames.pop()
        with open(bad, "w") as file:
            yaml.dump([], file)

        # Loading should not be an error as the files should not be reloaded.
        yaml_settings()

        # Test reloading with bad file.
        yaml_settings = CreateYamlSettings(*fileDummies, reload=True)

        with pytest.raises(PydanticSettingsYamlError) as err:
            yaml_settings()
            assert str(bad) in str(err)

        with open(bad, "w") as file:
            yaml.dump({}, file)

        yaml_settings()
