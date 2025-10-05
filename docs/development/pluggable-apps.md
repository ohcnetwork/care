# Pluggable Apps


## Overview

Care supports plugins that can be used to extend its functionality. Plugins are basically django apps that are defined in the `plug_config.py`.
These plugins can be automatically loaded during docker image build or run time, however its recommended to include them during docker image build time.
The default care image does not include any plugins, but you can create your own plugin config by overriding the `plug_config.py` file.


example `plug_config.py` file:

```python

from plugs.manager import PlugManager
from plugs.plug import Plug

my_plugin = Plug(
    name="my_plugin",
    package_name="git+https://github.com/octo/my_plugin.git",
    version="@v1.0.0",
    configs={
        "SERVICE_API_KEY": "my_api_key",
        "SERVICE_SECRET_KEY": "my_secret_key",
        "VALUE_1_MAX": 10,
    },
)

plugs = [my_plugin]

manager = PlugManager(plugs)
```

## Plugin config variables

Each plugin will define their own config variables with some defaults, they can also pick the values from the environment variables if required.
The order of precedence is as follows:

- Configs defined in the `plug_config.py`
- Environment variables
- Default values defined in the plugin


## Development

To get started with developing a plugin, use [care-plugin-cookiecutter](https://github.com/ohcnetwork/care-plugin-cookiecutter)
The plugin follows the structure of a typical django app where you can define your models, views, urls, etc. in the plugin folder.
The plugin manager will automatically load the required configurations and plugin urls under `/api/plugin-name/`.

To develop the plugins locally you can install the plugin in the editable mode using `pip install -e /path/to/plugin`.

If you need to inherit the components from the core app, you can install care in editable mode in the plugin using `pip install -e /path/to/care`.


## Available Plugins

- [Care Scribe](https://github.com/ohcnetwork/care_scribe): Care Scribe is a plugin that provides autofill functionality for the care consultation forms.
