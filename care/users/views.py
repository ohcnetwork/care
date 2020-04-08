import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django import forms
from care.users.forms import CustomSignupForm, User

from config.ratelimit import ratelimit

from django.conf import settings


def home_view(request):
    return render(request, "home.html")


class SignupView(View):
    form_class = CustomSignupForm
    template = "users/signup.html"

    def get(self, request, **kwargs):
        try:
            form = self.form_class()
            if kwargs["type"] != User.TYPE_VALUE_MAP["Volunteer"]:
                form.fields["skill"].widget = forms.HiddenInput()
            return render(
                request, self.template, {"form": form, "type": kwargs["name"]}
            )
        except Exception as e:
            print(e)
            logging.error(e)
            return HttpResponseRedirect("/500")

    def post(self, request, **kwargs):
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user_obj = form.save(commit=False)
            user_obj.user_type = kwargs["type"]
            if user_obj.user_type == 30:
                return HttpResponseRedirect("/500")
            user_obj.save()
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect("home")
        return render(request, self.template, {"form": form})


class SigninView(View):
    form_class = AuthenticationForm
    template = "users/login.html"

    def get(self, request, **kwargs):
        try:
            rate = False
            if ratelimit(request, "login", ["ip"]):
                rate = True
            form = self.form_class()
            return render(request, self.template, {"form": form, "rate": rate})
        except Exception as e:
            logging.error(e)
            return HttpResponseRedirect("/500")

    def post(self, request):
        form = AuthenticationForm(request=request, data=request.POST)
        if ratelimit(request, "login", [request.POST["username"]]):
            return render(request, self.template, {"form": form, "rate": True})
        form = AuthenticationForm(request=request, data=request.POST)
        next_url = request.GET.get("next", False)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            # return HttpResponse(status=404)
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    if next_url:
                        return HttpResponseRedirect(next_url)
                    return redirect("home")
        return render(request, self.template, {"form": form, "error": True})
