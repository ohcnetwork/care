import json
import logging
import os

from plug_config import manager
from plugs.plug import Plug

logger = logging.getLogger(__name__)


if ADDITIONAL_PLUGS := os.getenv("ADDITIONAL_PLUGS"):
    try:
        for plug in json.loads(ADDITIONAL_PLUGS):
            manager.add_plug(Plug(**plug))
    except json.JSONDecodeError:
        logger.error("ADDITIONAL_PLUGS is not a valid JSON")

manager.install()
