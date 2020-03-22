import logging

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.views import View
from django.http import HttpResponseRedirect

from care.users.forms import CustomSignupForm, User


def home_view(request):
    return render(request, "home.html")


class SignupView(View):
    form_class = CustomSignupForm
    template = "users/signup.html"

    def get(self, request, **kwargs):
        try:
            form = self.form_class()
            if kwargs["type"] != User.TYPE_VALUE_MAP['Volunteer']:
                form.fields.pop('skill')
            return render(
                request, self.template, {"form": form, "type": kwargs["name"]}
            )
        except Exception as e:
            logging.error(e)
            return HttpResponseRedirect("/500")

    def post(self, request, **kwargs):
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user_obj = form.save(commit=False)
            user_obj.user_type = kwargs["type"]
            user_obj.save()
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect("home")
        return render(request, self.template, {"form": form})


class SinginView(View):
    form_class = AuthenticationForm
    template = "users/login.html"

    def get(self, request, **kwargs):
        try:
            form = self.form_class()
            return render(request, self.template, {"form": form})
        except Exception as e:
            logging.error(e)
            return HttpResponseRedirect("/500")

    def post(self, request):
        form = AuthenticationForm(request=request, data=request.POST)
        next_url = request.GET.get("next", False)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    if next_url:
                        return HttpResponseRedirect(next_url)
                    return redirect("home")
        return render(request, self.template, {"form": form, "error": True})
