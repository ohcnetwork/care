from django.shortcuts import render
from rest_framework.response import Response


def home_view(request):
    return render(request, "pages/home.html")


def ping(request):
    return Response({"status": "OK"})
