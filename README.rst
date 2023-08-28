Why Should I Use This?
================================================================

This project is very helpful for projects that have large configuration files,
nested configuration files, or if you just don't like writing large ``.env``
files. It is also worth noting that due to the backwards compatability between
``YAML`` and ``JSON`` that this will also parse ``JSON`` configuration.

This can also be helpful when writing out application settings in kubernetes
/helm, where most configuration is written as ``YAML``. In such a case we may
want to validate/store our settings as ``YAML`` as writing ``JSON`` and
``JSON`` strings can be compersome due to syntax error in larger documents.

In the context of pipelines, it may be necessary to write an ``ENV`` file
template in line with your continuous integration or deployment variables.
However, this can be rather cumbersome due to escape sequences:

.. code:: yaml

  # Example pipeline with env settings
  # The configuration built is compatable with ``./tests/examples/__init__.py``

  ...
  pipelines:
    default:
      - step:
          name: Create settings for subsequent steps
          caches: pip
          script:
            - |
              export MYFISTSETTING="1"
              export MYDATABASESETTINGS="{
                \"host\" : \"localhost\",
                \"port\" : \"27017\",
                \"username\" : \"some\",
                \"password\" : \"dude\"
              }"
            - echo "MYFISTSETTING=$MYFISTSETTING" > .env
            - echo "MYDATABASESETTINGS=$MYDATABASESETTINGS" >> .env
          artifacts:
            - .env


The script section of the above bitbucket pipeline may be
replaced with something less horible to edit:

.. code:: yaml

  ...
  script:
    - |
      ENVYAMLCONTENT="{
        myFistSetting: 1
        myDatabaseSettings:
          host: localhost
          port: 27017
          username: some
          password: dude
      }"
    - echo $ENVYAMLCONTENT > .env
  ...


this may not make the strongest case due to the brevity of the settings
themselves. But when the settings are many layers deep, it is clear that
writing ``YAML`` is preferable as a result of the nicer syntax.


Installation
===============================================================================

Install using ``pip``:

.. code:: bash

  pip install yaml-settings-pydantic


Examples
===============================================================================

Please read `pydantics documentation about additional sources<https://docs.pydantic.dev/latest/usage/pydantic_settings/>`.

There are two classes worth knowing about:

- ``CreateYamlSettings`` -- The pydantic ``PydanticBaseSettingsSource`` that
  will analyze your class for the

  1. Files to be used -- under ``__env_yaml_settings_files__``.
  2. The reload settings -- under ``__env_yaml_settings_reload__``.

  This does not have to be used at all, but can be helpful if you don't want to
  use ``BaseYamlSettings`` for any reason.

- ``BaseYamlSettings`` -- Use this directly as done in the example below. This
  is 'the easy way'.


The shortest possible example is as follows:

.. code:: python

   from yaml_settings_pydantic import BaseYamlSettings

   class MySettings(BaseYamlSettings):
      __env_yaml_settings_files__ = ["settings.yaml"]

      setttingOne: str
      settingTwo: str
      ...

   ...


Also see the example in `./tests/examples/__init__.py`. It is gaurenteed to
work as its contents are tested and contain information on how to write nested
configurations.
