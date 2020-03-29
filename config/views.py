from django.shortcuts import render
import logging

def home_view(request):
    logging.basicConfig(level=logging.INFO)
    logging.info(request.META)
    return render(request, "pages/home.html")
