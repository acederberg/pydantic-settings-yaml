Why Should I Use This?
================================================================

This project is very helpful for projects that have large configuration files,
nested configuration files, or if you just don't like writing large ``.env``
files. It is also worth noting that due to the backwards compatability between
``YAML`` and ``JSON`` that this will also parse ``JSON`` configuration.

This can also be helpful when writing out (variables for ) helm charts,
pipelines of various sorts, and other ``YAML`` assets. In such a context, it
may be necessary to write an ``ENV`` file template in line with your continuous
integration or deployment variables. However, this can be rather cumbersome due
to escape sequences:

.. code:: yaml

  # Example pipeline with env settings
  # The configuration built is compatable with ``./examples/__init__.py``

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


this may not make the strongest case due to the brevity of the
settings themselves. But when the settings are many layers deep,
it is clear that writing ``YAML`` is preferable.


Examples, Usage, and Installation
================================================================

Install using ``pip``:

.. code:: bash

  pip install yaml-settings-pydantic

then import into your current project settings and modify your
configuration:

.. code:: python

  from yaml_settings_pydantic import create_settings_yaml
  from pydantic import BaseModel
  from pydantic.env_settings import BaseSettings, SettingsSourceCallable


  class SomeNestedSettings(BaseModel) :

    ...


  class MySettings(BaseSettings):

    class Config :

      env_settings_yaml = create_settings_yaml(
        "./path/to_my.yaml"
      )


      @classmethod
      def customise_sources(
          cls,
          init_settings: SettingsSourceCallable,
          env_settings: SettingsSourceCallable,
          file_secret_settings: SettingsSourceCallable,
      ):
          return (
              init_settings,
              env_settings,
              file_secret_settings,
              cls.env_yaml_settings,
          )

    mySetting: str

Finally it is useful to note that ``create_settings_yaml`` can accept multiple
files as input (all such inputs must deserialize to ``dict``) and reload them
on every call of ``env_settings_yaml`` or just on the origonal call using the
``reload`` parameter:

.. code:: python

  ...
  env_settings_yaml = create_settings_yaml(
    "./path/to/yaml_1.yaml",
    "./path/to_my.yaml",
    reload = True
  )
  ...

In this instance the values from ``./path/to_my.yaml`` will take precedence
over the ``YAML`` provided earlier. That is, the later in the input list the
path appears, the more its variables are prefered.
