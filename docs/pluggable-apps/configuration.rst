Pluggable Apps
==============

Care supports plugins that can be used to extend its functionality. Plugins are basically django apps that are defined in the `plug_config.py`.
These plugins can be automatically loaded during docker image build or run time, however its recommended to include them during docker image build time.
The default care image does not include any plugins, but you can create your own plugin config by overriding the `plug_config.py` file.


example `plug_config.py` file:

.. code-block:: python

    from plugs.manager import PlugManager
    from plugs.plug import Plug

    scribe_plug = Plug(
        name="care_scribe",
        package_name="git+https://github.com/coronasafe/care_scribe.git",
        version="@master",
        configs={
            "TRANSCRIBE_SERVICE_PROVIDER_API_KEY": "secret",
        },
    )

    plugs = [scribe_plug]

    manager = PlugManager(plugs)


Plugin config
-------------

Each plugin will define their own config with some defaults, they can also pick the values from the environment variables if required.
The order of precedence is as follows:

* Environment variables
* Configs defined in the `plug_config.py`
* Default values defined in the plugin
