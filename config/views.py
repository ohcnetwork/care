from django.http import JsonResponse
from django.shortcuts import render


def home_view(request):
    return render(request, "pages/home.html")


def ping(request):
    return JsonResponse({"status": "OK"})
