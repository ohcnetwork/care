import environ

from plugs.manager import PlugManager
from plugs.plug import Plug  # noqa F401

env = environ.Env()

plugs = []

manager = PlugManager(plugs)
