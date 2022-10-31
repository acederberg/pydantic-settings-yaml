from os import path

from pydantic import BaseModel, BaseSettings
from pydantic.env_settings import SettingsSourceCallable
from pydantic_settings_yaml import create_yaml_settings


class MySettings(BaseSettings):

    # This is the important stuff that implements the function
    # in question.
    class Config:

        # Use reload to determine if create_yaml_settings will
        # load and parse the provided files every time it is
        # called.
        env_yaml_settings = create_yaml_settings(
            path.realpath(path.join(path.dirname(__file__), "example.yaml")),
            reload=False,
        )
        env_file = "exmaple.env"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ):

            # The order in which these appear determines their
            # precendence. So a ``.env`` file could be added to
            # override the ``YAML`` configuration.
            return (
                init_settings,
                # env_settings, # Uncomment this line to load from ``example.ymal``.
                file_secret_settings,
                cls.env_yaml_settings,
            )

    # Nested configuration example.
    class MyDataBaseSettings(BaseModel):

        host: str
        port: int
        username: str
        password: str

    myFistSetting: int
    myDatabaseSettings: MyDataBaseSettings


if __name__ == "__main__":

    # Print out parsed settings as q dict/json.
    import json
    from shutil import get_terminal_size

    sep = get_terminal_size().columns * "="
    settings = MySettings()

    print(sep)
    print("Results parsed from 'example.yaml':")
    print(
        json.dumps(
            settings.dict(),
            default=str,
            indent=2,
        )
    )
    print(sep)
