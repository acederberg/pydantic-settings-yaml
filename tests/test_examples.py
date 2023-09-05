import json
import os
import subprocess
from os import path
from unittest import mock

import docker
from docker.client import DockerClient
from pydantic_core import ValidationError
from pydantic_settings import SettingsConfigDict

from .examples import MySettings as Settings


class TestExampleCanOverWrite:
    env_extras = dict(
        MY_SETTINGS_MYFIRSTSETTING="9999",
        MY_SETTINGS_MYDATABASESETTINGS__HOSTSPEC__HOST="12.34.56.78",
    )

    def test_init(self):
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
        s = Settings(**raw)

        assert s.myFirstSetting == 1234, "Failed to load first levl settings."
        assert (
            s.myDatabaseSettings.hostspec.username == "cornpuff"
        ), "Failed to load nested configuration."

    @mock.patch.dict(os.environ, **env_extras)
    def test_envvars(self):
        """Environment variables should be able to overwrite YAML
        configuration."""

        s = Settings()
        expected = int(self.env_extras["MY_SETTINGS_MYFIRSTSETTING"])
        assert s.myFirstSetting == expected

        field = "MY_SETTINGS_MYDATABASESETTINGS__HOSTSPEC__HOST"
        expected = self.env_extras[field]
        assert s.myDatabaseSettings.hostspec.host == expected

    @mock.patch.dict(os.environ, **env_extras)
    def test_envvars_after_init(self):
        """Environment variables should take presendence by init."""

        expectedMyFirstSetting = 11111111
        s = Settings(myFirstSetting=expectedMyFirstSetting)
        assert s.myFirstSetting == expectedMyFirstSetting

    def test_dotenv(self):
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
        SettingsWEnv = type("MySettingsWEnv", (Settings,), namespace)
        s = SettingsWEnv()
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


def test_example_execution():
    result = subprocess.run(
        ["python", "-m", "tests.examples"],
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
    assert result.returncode == 0
    assert (out := result.stdout)
    assert not result.stderr

    out = out.decode()
    out = out.split("\n")
    assert "=============" in out[0]
    assert "=============" in out[-2]
    assert "Result" in out[1]

    # Verify that the body is valid JSON
    result = "".join(out[2:-2])
    result = json.loads(result)
