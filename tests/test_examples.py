import json
import subprocess

import pytest
from pydantic_core import ValidationError

from .examples import MySettings as Settings


class TestExampleCanOverWrite:
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

        assert s.myFirstSetting == 1234, "Failed to load first level settings."
        assert (
            s.myDatabaseSettings.hostspec.username == "cornpuff"
        ), "Failed to load nested configuration."

    def test_envvars(self):
        """Environment variables should be able to overwrite YAML
        configuration."""

        s = Settings()

    def test_envvars_after_init(self):
        """Environment variables should be overwritten by init."""
        ...


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
