import json
import os
import subprocess
from os import path
from typing import List, Optional
from unittest import mock

import pytest
from pydantic_settings import SettingsConfigDict

from .examples import ExplicitSettings, MinimalSettings, SubpathSettings


@pytest.mark.parametrize(
    "Settings", [ExplicitSettings, MinimalSettings, SubpathSettings]
)
class TestExampleCanOverWrite:
    env_extras = dict(
        MY_SETTINGS_MYFIRSTSETTING="9999",
        MY_SETTINGS_MYDATABASESETTINGS__HOSTSPEC__HOST="12.34.56.78",
    )

    def test_init(self, Settings):
        raw = dict(
            myFirstSetting=1234,
            myDatabaseSettings=dict(  # type: ignore
                connectionspec=dict(),
                hostspec=dict(
                    username="cornpuff",
                    password="the thing, you know, the thing",
                ),
            ),
        )
        s = Settings(**raw)  # type: ignore

        assert s.myFirstSetting == 1234, "Failed to load first levl settings."
        assert (
            s.myDatabaseSettings.hostspec.username == "cornpuff"
        ), "Failed to load nested configuration."

    @mock.patch.dict(os.environ, **env_extras)
    def test_envvars(self, Settings):
        """Environment variables should be able to overwrite YAML
        configuration."""

        s = Settings()  # type: ignore
        expected = int(self.env_extras["MY_SETTINGS_MYFIRSTSETTING"])
        assert s.myFirstSetting == expected

        field = "MY_SETTINGS_MYDATABASESETTINGS__HOSTSPEC__HOST"
        expected = self.env_extras[field]
        assert s.myDatabaseSettings.hostspec.host == expected

    @mock.patch.dict(os.environ, **env_extras)
    def test_envvars_after_init(self, Settings):
        """Environment variables should take presendence by init."""

        expectedMyFirstSetting = 11111111
        s = Settings(myFirstSetting=expectedMyFirstSetting)  # type: ignore
        assert s.myFirstSetting == expectedMyFirstSetting

    def test_dotenv(self, Settings):
        model_config = SettingsConfigDict(
            env_prefix="MY_SETTINGS_",
            env_nested_delimiter="__",
            env_file=path.join(
                path.dirname(__file__),
                "examples",
                "example.env",
            ),
        )
        namespace = dict(model_config=model_config)
        SettingsWEnv = type("ExplicitSettingsWEnv", (Settings,), namespace)
        s = SettingsWEnv()  # type: ignore
        assert s.myFirstSetting == 8888
        assert s.myDatabaseSettings.hostspec.host == "5.4.3.2"

    '''
    def test_file_secret_settings(self) -> None:
        """Reproduces the functionality described in the
        `pydantic docs<docs.pydantic.dev/latest/usage/pydantic_settings/>`.

        Will require docker in pipelines.
        """
        client: DockerClient = docker.from_env()

        client.containers.run("python:latest", name="ysp-test-container")
        client.secrets.create(name="ysp-test-secret", data="")
        '''


@pytest.mark.parametrize(
    "subcommand",
    [None, "minimal-settings", "explicit-settings", "subpath-settings"],
)
def test_example_execution(subcommand: Optional[str]):
    command = ["python", "-m", "tests.examples"]
    if subcommand is not None:
        command.append(subcommand)
    result = subprocess.run(
        command,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
    out: str | List[str]
    assert result.returncode == 0
    assert (out := result.stdout.decode())
    assert not result.stderr

    out = out.split("\n")
    assert "=============" in out[0]
    assert "=============" in out[-2]
    assert "Result" in out[1]

    # Verify that the body is valid JSON
    result = "".join(out[2:-2])
    result = json.loads(result)
