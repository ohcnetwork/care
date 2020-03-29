import logging

from django.views.generic import TemplateView


def home_view(request):
    logging.basicConfig(level=logging.INFO)
    logging.info(request.META)
    return TemplateView.as_view(template_name="pages/home.html")
