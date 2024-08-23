from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render


def app_version(_):
    return JsonResponse({"version": settings.APP_VERSION})


def home_view(request):
    return render(request, "pages/home.html")


def ping(_):
    return JsonResponse({"status": "OK"})
