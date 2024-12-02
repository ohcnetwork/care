from datetime import datetime
from json import JSONEncoder
from logging import getLogger

logger = getLogger(__name__)


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        if isinstance(o, datetime):
            return o.isoformat()
        logger.warning("Serializing Unknown Type %s, %s", type(o), o)
        return str(o)
