from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from care.utils.metrics import metrics_registry


def app_version(request):
    return JsonResponse({"version": settings.APP_VERSION})


def home_view(request):
    return render(request, "pages/home.html")


def ping(request):
    return JsonResponse({"status": "OK"})


@never_cache
@require_safe
def metrics(request):
    return HttpResponse(
        generate_latest(metrics_registry), content_type=CONTENT_TYPE_LATEST
    )
