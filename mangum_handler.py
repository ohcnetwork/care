import os

from asgiref.wsgi import WsgiToAsgi
from django.core.wsgi import get_wsgi_application
from mangum import Mangum

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "care.config.settings")

application = WsgiToAsgi(get_wsgi_application())

handler = Mangum(application, lifespan="off")
