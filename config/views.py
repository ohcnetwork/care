from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from prometheus_client import CONTENT_TYPE_LATEST

from care.utils.metrics import get_metrics_payload


def app_version(request):
    return JsonResponse({"version": settings.APP_VERSION})


def home_view(request):
    return render(request, "pages/home.html")


def ping(request):
    return JsonResponse({"status": "OK"})


@transaction.non_atomic_requests
@never_cache
@require_safe
def metrics(request):
    return HttpResponse(get_metrics_payload(), content_type=CONTENT_TYPE_LATEST)
