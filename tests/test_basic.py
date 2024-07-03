from __future__ import annotations

import os
import pathlib
from pathlib import Path
from typing import Annotated, Any
from unittest import mock

import pytest
import yaml
from pydantic import BaseModel, Field

from yaml_settings_pydantic import (
    DEFAULT_YAML_FILE_CONFIG_DICT,
    BaseYamlSettings,
    CreateYamlSettings,
    YamlFileConfigDict,
    YamlSettingsConfigDict,
    resolve_filepaths,
)

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


class TestCreateYamlSettings:
    def test_reload(self, file_dummies: Any) -> None:
        # Test args
        with pytest.raises(ValueError):
            CreateYamlSettings(BaseYamlSettings)

        # Make sure it works. Check name of returned learcal
        def create_settings(reload: Any | None = None, files: Any | None = None) -> Any:
            return type(
                "Settings",
                (BaseYamlSettings,),
                {
                    "__yaml_reload__": reload or False,
                    "__yaml_files__": files or set(file_dummies),
                },
            )

        Settings = create_settings()
        yaml_settings = CreateYamlSettings(Settings)
        yaml_settings()

        assert not yaml_settings.reload, "Should not reload."

        # Malform a file.
        bad: Path = Settings.__yaml_files__.pop()
        with bad.open("w") as file:
            yaml.dump([], file)

        # # NOTE: Loading should not be an error as the files should not be reloaded.
        yaml_settings()
        #
        # # NOTE: Test reloading with bad file.
        # #       This could be called without the args as mutation is visible
        # #       to fn.
        Settings = create_settings(reload=False)
        yaml_settings = CreateYamlSettings(Settings)

        with pytest.raises(ValueError) as err:
            yaml_settings()

        assert bad.as_posix() in str(err.value), "Missing required path in message."

        with bad.open("w") as file:
            yaml.dump({}, file)

        yaml_settings()

    def from_model_config(
        self, **kwargs: Any
    ) -> tuple[CreateYamlSettings, type[BaseYamlSettings]]:
        Settings = type(
            "Settings",
            (BaseYamlSettings,),
            {"model_config": YamlSettingsConfigDict(**kwargs)},  # type: ignore
        )
        return CreateYamlSettings(Settings), Settings

    def test_dunders_have_priority(self) -> None:
        init_reload = True
        foo_bar: Path = Path("foo-bar.yaml")
        yaml_settings, Settings = self.from_model_config(
            yaml_files={foo_bar},
            yaml_reload=init_reload,
        )

        default = DEFAULT_YAML_FILE_CONFIG_DICT
        assert yaml_settings.files == {foo_bar: default}
        assert yaml_settings.reload == init_reload

        final_files: set[Path] = {Path("spam-eggs.yaml")}
        OverwriteSettings = type(
            "OverwriteSettings",
            (Settings,),
            {"__yaml_files__": final_files},
        )
        yaml_settings = CreateYamlSettings(OverwriteSettings)

        assert yaml_settings.files == {Path("spam-eggs.yaml"): default}
        assert yaml_settings.reload == init_reload

    @pytest.mark.parametrize(
        "yaml_files",
        [
            Path("foo.yaml"),
            {Path("foo.yaml")},
            {Path("foo.yaml"): YamlFileConfigDict(required=True, subpath=None)},
        ],
    )
    def test_hydration_yaml_files(self, yaml_files: Any) -> None:
        make, _ = self.from_model_config(yaml_files=yaml_files)

        assert len(make.files) == 1, "Exactly one file."
        assert isinstance(make.files, dict), "Files should hydrate to a ``dict``."
        assert (
            foo := make.files.get(Path("foo.yaml"))
        ), "An entry should exist under key ``Path('foo.yaml')``."
        assert isinstance(foo, dict), "`foo` must be a dictionary."
        assert foo.get("required"), "Required is always ``True`` by default."
        assert not foo.get("subpath"), "Subpath is never set."

    def test_yaml_not_required(self) -> None:
        # Should not raise error
        make, Settings = self.from_model_config(
            yaml_files={
                Path("foo.yaml"): YamlFileConfigDict(
                    required=False,
                    subpath=None,
                ),
            },
        )
        if not make.files.get(Path("foo.yaml")):
            raise ValueError
        make.load()

        # Should raise error
        make, _ = self.from_model_config(yaml_files=Path("foo.yaml"))
        with pytest.raises(ValueError) as err:
            make.load()

        assert str(err.value)

    def test_envvar(self, tmp_path: pathlib.Path) -> None:

        # ------------------------------------------------------------------- #
        # NOTE: Settup

        path_default = tmp_path / "default.yaml"
        path_other = tmp_path / "other.yaml"

        make, _Settings = self.from_model_config(
            yaml_files={
                path_default: YamlFileConfigDict(
                    envvar="FOO_PATH",
                    required=False,
                    subpath=None,
                )
            }
        )
        assert set(make.files.keys()) == {path_default}

        class SettingsModel(BaseModel):
            whatever: Annotated[str, Field(default="whatever")]

        class Settings(SettingsModel, _Settings): ...  # type: ignore

        default = SettingsModel(whatever="default")
        other = SettingsModel(whatever="other")

        with Path.open(path_default, "w") as file_default, Path.open(
            path_other, "w"
        ) as file_other:
            yaml.dump(default.model_dump(mode="json"), file_default)
            yaml.dump(other.model_dump(mode="json"), file_other)

        # ------------------------------------------------------------------- #
        # NOTE: Actual tests.

        with mock.patch.dict(os.environ, {"FOO_PATH": str(path_other)}, clear=True):
            filepath_resolved = resolve_filepaths(
                path_default,
                make.files[path_default],
            )
            assert filepath_resolved == path_other

            # NOTE: Now testing loading.
            settings = Settings.model_validate({})
            assert settings.whatever == "other"

        with mock.patch.dict(os.environ, {"FOO_PATH": ""}, clear=True):
            filepath_resolved = resolve_filepaths(
                path_default,
                make.files[path_default],
            )
            assert filepath_resolved == path_default

            settings = Settings.model_validate({})
            assert settings.whatever == "default"
