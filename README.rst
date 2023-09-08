
What?
===============================================================================

A simple tool for loading ``YAML`` and ``JSON`` configuration/settings using
``pydantic2``.

There is also a version for ``pydantic1``, see ``release/v1``. Major
versions of this package will match the major version of the respective
``pydantic`` release.


Why?
===============================================================================

This project can be helpful for projects that have large configuration files,
nested configuration files, or for those of us who don't like writing large ``.env``
files. It is also worth noting that due to the backwards compatability between
``YAML`` and ``JSON`` that this will also parse ``JSON`` configuration.

This can also be helpful when writing out application settings in kubernetes
/helm, where most configuration is written as ``YAML``. In such a case we may
want to validate/store our settings as ``YAML`` as writing ``JSON`` and
``JSON`` strings can be compersome due to syntax error in larger documents.


Installation
===============================================================================


Install using ``pip``:

.. code:: bash

  pip install yaml-settings-pydantic



Examples
===============================================================================

Additional information
-------------------------------------------------------------------------------

First, it is worth reading the ``pydantic_settings`` docs about additional sources: https://docs.pydantic.dev/latest/usage/pydantic_settings/

Additionally see the example in ``./tests/examples/__init__.py``. It is gaurenteed to
work as its contents are tested. It contains information on how to write nested
configurations.


Tools
-------------------------------------------------------------------------------

There are three classes worth knowing about:

- ``YamlSettingsConfigDict`` -- ``pydantic_settings.SetttingsConfigDict``
  extended to include the fields used by ``CreateYamlSettings``.
- ``CreateYamlSettings`` -- The pydantic ``PydanticBaseSettingsSource`` that
  will analyze your class for the following class variables:

  1. Files to be used -- under ``__env_yaml_files__`` or ``model_config.yaml_files``.
  2. The reload settings -- under ``__env_yaml_reload__`` or ``model_config.yaml_reload``.

  ``CreateYamlSettings`` does not have to be used at all, but can be helpful if
  you don't want to use ``BaseYamlSettings`` for any reason.

- ``BaseYamlSettings`` -- Use this directly as done in the example below. This
  is 'the easy way'.


Minimal Examples
-------------------------------------------------------------------------------

The shortest possible example is as follows:

.. code:: python

   from yaml_settings_pydantic import BaseYamlSettings

   class MySettings(BaseYamlSettings):
      __env_yaml_files__ = "settings.yaml"

      setttingOne: str
      settingTwo: str
      ...

   ...


Note that the above example can also be written like


.. code:: python

   from yaml_settings_pydantic import BaseYamlSettings, YamlSettingsConfigDict

   class MySettings(BaseYamlSettings):
      model_config = YamlSettingsConfigDict(yaml_files="settings.yaml")

      setttingOne: str
      settingTwo: str
      ...

   ...


which is more like pydantic v2. The 'dunder' specifications will take priority
over their equivalent `model_config` specifications. These map as follows:

.. code:: text

  +-----------------------+------------------+
  | dunder                | model_config     |
  +-----------------------+------------------+
  | __env_yaml_files__    | yaml_files       |
  | __env_yaml_reload__   | yaml_reload      |
  +-----------------------+------------------+
