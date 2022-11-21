from typing import (Any, Callable, Dict, Iterable, Iterator, List, Optional,
                    Tuple, Union)

from pydantic import validate_arguments
from pydantic.env_settings import SettingsSourceCallable
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

    files = {filepath: open(filepath) for filepath in filepaths}
    loaded_files: Dict[str, Dict] = {
        file_name: safe_load(file) for file_name, file in files.items()
    }
    next((None for file in files.values() if file.close() is not None), None)
    return loaded_files


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

    def yaml_loadmanyandvalidate() -> Dict:
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
            name
            for name, content in loaded_files.items()
            if not isinstance(content, dict)
        )
        if len(isnotadict) > 0:
            raise PydanticSettingsYamlError(
                f"Invalid file format: The files ``{isnotadict}`` do not"
                f"deserialize to dictionaries."
            )

        return _recursive_merge(iter(loaded_files.values()))

    if not reload:

        loaded = yaml_loadmanyandvalidate()

        def yaml_settings(settings: SettingsSourceCallable) -> Dict:
            return loaded

        return yaml_settings

    def yaml_settings_many(settings: SettingsSourceCallable) -> Dict:
        return yaml_loadmanyandvalidate()

    return yaml_settings_many


"""
class BaseYamlSettings:
    ...
"""
