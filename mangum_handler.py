# asgi.py
import os
from mangum import Mangum
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

application = get_wsgi_application()

handler = Mangum(application, lifespan="off")
