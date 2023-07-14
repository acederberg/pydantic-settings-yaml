from os import path
from typing import Any, Callable, ClassVar, Dict, Optional, Tuple, Type

from pydantic.v1.utils import deep_update
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from yaml import safe_load


class PydanticSettingsYamlError(Exception):
    """Error for this package."""

    ...


def loadmanyandvalidate(*filepaths: str) -> Dict[str, Any]:
    """Load data and validate that it is sufficiently shaped for
    ``BaseSettings``.

    :param filepaths: Paths to the `YAML` files to load and validate.
    :raises: :class:`PydanticSettingsYamlError` when any of the files do not
        deserialize to a dictionary.
    :returns: Loaded files.
    """

    # Make sure paths at least exist.
    bad = tuple(fp for fp in filepaths if not path.isfile(fp))
    if bad:
        raise ValueError(f"The following paths are not files: ``{bad}``.")

    # Bulk load files (and bulk manage IO closing/opening).
    files = {filepath: open(filepath) for filepath in filepaths}
    loaded: Dict[str, Dict] = {
        filepath: safe_load(file) for filepath, file in files.items()
    }
    for file in files.values():
        file.close()

    # Bulk validate. Settings requires key value pairs.
    if bad := tuple(
        filepath
        for filepath, filecontent in loaded.items()
        if not isinstance(filecontent, dict)
    ):
        raise PydanticSettingsYamlError(
            f"Invalid file format: The files ``{bad}`` must"
            f"deserialize to dictionaries."
        )

    out: Dict[str, Any]
    deep_update(out := {}, *loaded)
    return out


def create_yaml_settings(
    *filepaths: str,
) -> Callable[[PydanticBaseSettingsSource], Dict]:
    """Create a ``yaml`` setting loader middleware.

    Using this properly will help you not reload the files provided.
    To disable this, set :param:``reload`` tu ``True``.
    :param filepaths: ``YAML`` or ``JSON`` to load.
    :raises ValueError: When :param:``filepaths`` has length 0.
    :returns: A middleware to load files specified by the filepaths.
    """

    n = len(filepaths)
    if n == 0:
        raise ValueError("Atleast one file is required.")

    loaded = loadmanyandvalidate(*filepaths)

    def yaml_settings(
        settings: Optional[PydanticBaseSettingsSource],
    ) -> Dict[str, Any]:
        """Yaml settings loader for a single file."""
        return loaded

    return yaml_settings


class BaseYamlSettings:
    # Use reload to determine if create_yaml_settings will
    # load and parse the provided files every time it is
    # called.
    __env_yaml_settings_files__: ClassVar[Tuple[str, ...]]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Look for env files.
        files = getattr(cls, eysf := "__env_yaml_settings_files__", None)
        if files is None:
            msg = f"`{eysf}` is required."
            raise PydanticSettingsYamlError(msg)

        yaml_settings = create_yaml_settings(*files)

        # The order in which these appear determines their precendence. So a
        # ``.env`` file could be added to # override the ``YAML`` configuration
        return (
            init_settings,
            env_settings,
            yaml_settings,
            dotenv_settings,
            file_secret_settings,
        )


__all__ = (
    "loadmanyandvalidate",
    "create_yaml_settings",
    "BaseYamlSettings",
)
