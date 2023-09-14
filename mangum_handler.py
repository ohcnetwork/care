import os
import sys

from a2wsgi import WSGIMiddleware
from django.core.wsgi import get_wsgi_application
from mangum import Mangum

app_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
)
sys.path.append(os.path.join(app_path, "care"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

wsgi_application = get_wsgi_application()

application = WSGIMiddleware(wsgi_application)

handler = Mangum(application, lifespan="off")
