from os import path
from typing import (Any, Callable, Dict, Iterable, Iterator, List, Optional,
                    Tuple, Union)

from pydantic import validate_arguments
from pydantic.env_settings import BaseSettings, SettingsSourceCallable
from yaml import safe_load


class PydanticSettingsYamlError(Exception):
    ...


def __recursive_merge(
    to_combine: Optional[Dict],
    already_combined: Dict,
) -> None:
    """Recursive merge helper. Thank you `stack exchange<https://bit.ly/3SJcASN>`!

    :param to_combine: Dictionary to merge in.
    :param already_combined: Dictionary to merge into.
    :returns: Nothing.
    """

    if to_combine is None:
        return
    for key, value in to_combine.items():
        if isinstance(value, dict):
            __recursive_merge(value, already_combined.setdefault(key, value))
        else:
            already_combined[key] = value


def _recursive_merge(items: Iterator[Dict]) -> Dict:
    """Nondestrucively deep merge dictionaries.

    Objects take precendence as presented in the input.
    :param items: The various items to merge into one object.
    :returns: Merge produce.
    """

    out: Dict = {}
    _ = all(__recursive_merge(item, out) is None for item in items)
    return out


@validate_arguments
def _load_many(*filepaths: str) -> Dict[str, Any]:

    bad = tuple(fp for fp in filepaths if not path.isfile(fp))
    if bad:
        raise ValueError(f"The following paths are not files: ``{bad}``.")

    files = {filepath: open(filepath) for filepath in filepaths}
    loaded_files: Dict[str, Dict] = {
        file_name: safe_load(file) for file_name, file in files.items()
    }
    next((None for file in files.values() if file.close() is not None), None)
    return loaded_files


def yaml_loadmanyandvalidate(*filepaths: str) -> Dict:
    """Load data and validate that it is sufficiently shaped for
    ``BaseSettings``.

    :raises PydanticSettingsYamlError: When any of the files do not
        deserialize to a dictionary.
    :returns: Loaded files.
    """

    # bulk load files. use comprehensions.
    loaded_files: Dict[str, Dict] = _load_many(*filepaths)

    # Bulk validate. Settings requires key value pairs.
    isnotadict = tuple(
        name for name, content in loaded_files.items() if not isinstance(content, dict)
    )
    if len(isnotadict) > 0:
        raise PydanticSettingsYamlError(
            f"Invalid file format: The files ``{isnotadict}`` do not"
            f"deserialize to dictionaries."
        )

    return _recursive_merge(iter(loaded_files.values()))


def create_yaml_settings(
    *filepaths: str,
    reload: bool = True,
) -> Callable[[SettingsSourceCallable], Dict]:
    """Create a ``yaml`` setting loader middleware.

    Using this properly will help you not reload the files provided.
    To disable this, set :param:``reload`` tu ``True``.
    :param filepaths: ``YAML`` or ``JSON`` to load.
    :param reload: Always reload the files when ``True``.
    :raises ValueError: When :param:``filepaths`` is not sufficiently long,
        e.g. when it has length 0.
    :returns: A middleware to load files specified by the filepaths.


    Use cases involve nested schemas, which can be helpful when there are a
    large number of settings that serve various purposes. For instance the
    flollowing:

    .. literal_include:: ../example/__init__.py
       :language: python

    Would parse the following yaml settings.

    .. literal_include:: ../example/example.yaml
       :language: yaml

    """

    n = len(filepaths)
    if n == 0:
        raise ValueError("Atleast one file is required.")

    if not reload:

        loaded = yaml_loadmanyandvalidate(*filepaths)

        def yaml_settings(settings: Optional[SettingsSourceCallable]) -> Dict:
            """Yaml settings loader for a single file."""
            return loaded

        return yaml_settings

    def yaml_settings_reload(settings: Optional[SettingsSourceCallable]) -> Dict:
        """Yaml settings loader for many files."""
        return yaml_loadmanyandvalidate(*filepaths)

    return yaml_settings_reload

class BaseYamlSettingsConfig:

    # Use reload to determine if create_yaml_settings will
    # load and parse the provided files every time it is
    # called.
    env_yaml_settings_files: Tuple[str, ...]
    env_yaml_settings: SettingsSourceCallable
    env_yaml_settings_ignore_env_file: bool = True
    env_yaml_settings_reload: bool = True

    @classmethod
    @validate_arguments
    def validate_internals(
        cls,
        env_yaml_settings_files: Optional[Tuple[str, ...]] = None,
        env_yaml_settings: Optional[SettingsSourceCallable] = None,
        env_yaml_settings_ignore_env_file: bool = True,
        env_yaml_settings_reload: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Validation of internals."""
        out = {}
        env_yaml_settings = getattr(cls, "env_yaml_settings", None)
        env_yaml_settings_files = getattr(cls, "env_yaml_settings_files", None)

        if env_yaml_settings is None:
            if not env_yaml_settings_files:
                raise PydanticSettingsYamlError(
                    "Either ``env_yaml_settings`` or ``env_setting_yaml_file`` is required."
                )
            out["env_yaml_settings"] = create_yaml_settings(
                *env_yaml_settings_files,
                reload=getattr(cls, "env_yaml_settings_reload", False),
            )

        return out

    @classmethod
    def customise_sources(
        cls,
        init_settings: SettingsSourceCallable,
        env_settings: SettingsSourceCallable,
        file_secret_settings: SettingsSourceCallable,
    ):

        attrs = {
            f"env_yaml_settings{s}": getattr(cls, f"env_yaml_settings{s}", None)
            for s in (
                "_files",
                "",
                "_ignore_env_file",
                "_reload",
            )
        }
        attrs.update(cls.validate_internals(**attrs))
        files, env_yaml_settings, _, _ = attrs.values()

        if files and env_settings is None:
            cls.env_yaml_settings = create_yaml_settings(*files)

        # The order in which these appear determines their
        # precendence. So a ``.env`` file could be added to
        # override the ``YAML`` configuration.
        callables = (
            init_settings,
            file_secret_settings,
            env_yaml_settings,
        )
        return (
            callables
            if attrs["env_yaml_settings_ignore_env_file"]
            else (*callables, env_settings)
        )

__all__ = ( 
    "yaml_loadmanyandvalidate", 
    "create_yaml_settings", 
    "BaseYamlSettingsConfig" 
)


