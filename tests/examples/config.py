from os import path
from typing import Dict

from pydantic import BaseModel
from yaml_settings_pydantic import BaseYamlSettings


class MySettings(BaseYamlSettings):
    """ """

    # Dunders implement which files will be used and how.
    # This one specifies the files to be used. Multiple files can be used.
    # Make sure that this is a tuple.
    __env_yaml_settings_files__ = (
        path.realpath(path.join(path.dirname(__file__), "example.yaml")),
    )

    # Use reload to determine if CreateYamlSettings will load and parse the
    # provided files every time it is called.
    __env_yaml_settings_reload__ = True

    # Nested configuration example.
    class MyDataBaseSettings(BaseModel):
        class MyNestedDatabaseSettings(BaseModel):
            host: str
            port: int
            username: str
            password: str

        connectionspec: Dict[str, str]
        hostspec: MyNestedDatabaseSettings

    myFirstSetting: int
    myDatabaseSettings: MyDataBaseSettings
