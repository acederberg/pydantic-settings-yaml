from os import path
from pathlib import Path

from yaml_settings_pydantic import (
    BaseYamlSettings,
    YamlFileConfigDict,
    YamlSettingsConfigDict,
)

WHATEVER = Path(__file__).parent / "extra" / "whatever.yaml"


def test_yaml_files_dict_string_keys():
    """For now, make sure that this does not fail."""

    class Settings(BaseYamlSettings):
        the: str
        should: str
        here: str | None

        model_config = YamlSettingsConfigDict(
            yaml_files={
                WHATEVER: YamlFileConfigDict(
                    subpath="whatever",
                    required=True,
                )
            }
        )

    settings = Settings.model_validate({})
    assert settings.the == "heck"
    assert settings.should == "be"
    assert settings.here is None
