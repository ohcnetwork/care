import logging

from django.views.generic import TemplateView

from django.shortcuts import render


def home_view(request):
    logging.basicConfig(level=logging.INFO)
    logging.info(request.META)
    return render(request, "pages/home.html")
