from os import path
from typing import Dict

from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict
from yaml_settings_pydantic import (
    BaseYamlSettings,
    YamlFileConfigDict,
    YamlSettingsConfigDict,
)


def herepath(fn: str) -> str:
    return path.realpath(path.join(path.dirname(__file__), fn))


class MinimalSettings(BaseYamlSettings):
    """Example settings.

    :class MyDataBaseSettings: Schema for the nested field.
    :attr myFirstSettings: A scalar field.
    :attr myDatabaseSettings: A nested field.
    """

    model_config = YamlSettingsConfigDict(
        env_prefix="MY_SETTINGS_",
        env_nested_delimiter="__",
        yaml_files={herepath("my-settings.yaml")},
    )

    # Nested configuration example.
    class MyDataBaseSettings(BaseModel):
        "Dummy schema for nested."

        class MyNestedDatabaseSettings(BaseModel):
            "Second order nested schema."
            host: str
            port: int
            username: str
            password: str

        connectionspec: Dict[str, str]
        hostspec: MyNestedDatabaseSettings

    # Configuration fields.
    myFirstSetting: int
    myDatabaseSettings: MyDataBaseSettings


class ExplicitSettings(MinimalSettings):
    """Example settings with explicit loading rules."""

    # ----------------------------------------------------------------------- #
    #                                                                         #
    # ``yaml_files`` can be a string (A path to one file), a sequence, a set, #
    # or a ditionary with string keys and ``YamlFileConfigDict`` as values.   #
    # In the case that ``yaml_files`` is any of the first three, it is        #
    # equivalent to using the item(s) as key(s) with ``YamlFileConfigDict``   #
    # values as below with the value below.                                   #
    #                                                                         #
    # NOTE: Attributes set on :class:`MyMinimalSettings` should be present    #
    #       here. Do not remove this comment, it is intended for those not    #
    #       familiar with pydantic.                                           #
    #                                                                         #
    # ----------------------------------------------------------------------- #

    model_config = YamlSettingsConfigDict(
        env_prefix="MY_SETTINGS_",
        env_nested_delimiter="__",
        yaml_files={
            herepath("my-settings.yaml"): YamlFileConfigDict(
                subpath=None, required=True
            )
        },
        yaml_reload=True,
    )

    # ----------------------------------------------------------------------- #
    #                                                                         #
    # Dunders implement which files will be used and how.                     #
    # This one specifies the files to be used. Multiple files can be used.    #
    # This can overwrite a model_config["yaml_files"]                         #
    #                                                                         #
    # ----------------------------------------------------------------------- #

    # __yaml_files__ = (
    #     path.realpath(
    #         path.join(path.dirname(__file__), "example.yaml")
    #     ),
    # )

    # ----------------------------------------------------------------------- #
    #                                                                         #
    # Use reload to determine if CreateYamlSettings will load and parse the   #
    # provided files every time it is called.                                 #
    #                                                                         #
    # ----------------------------------------------------------------------- #

    # __yaml_reload__ = True


class SubpathSettings(ExplicitSettings):
    """Example for loading settings from some subpath."""

    # ----------------------------------------------------------------------- #
    #                                                                         #
    # The following example makes it such that the YAML file is required but  #
    # the configuration defined in ``ExplicitSettings`` is nested somewhere in a    #
    # YAML.                                                                   #
    #                                                                         #
    # For details what is supported for subpath, see ``jsonpath-ng`` on PyPI:
    # https://pypi.org/project/jsonpath-ng/
    #
    #                                                                         #
    # ----------------------------------------------------------------------- #

    model_config = YamlSettingsConfigDict(
        env_prefix="MY_SETTINGS_",
        env_nested_delimiter="__",
        yaml_files={
            herepath("subpath-settings.yaml"): YamlFileConfigDict(
                subpath="nested.config.[0]",
                required=True,
            )
        },
        yaml_reload=True,
    )
