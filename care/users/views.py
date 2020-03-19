# from django.contrib import messages
# from django.contrib.auth import get_user_model
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.urls import reverse
# from django.utils.translation import ugettext_lazy as _
# from django.views.generic import DetailView, RedirectView, UpdateView


from django.shortcuts import render
from django.contrib.auth import login, authenticate
from care.users.forms import CustomSignupForm
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponseRedirect


# User = get_user_model()


# class UserDetailView(LoginRequiredMixin, DetailView):

#     model = User
#     slug_field = "username"
#     slug_url_kwarg = "username"


# user_detail_view = UserDetailView.as_view()


# class UserUpdateView(LoginRequiredMixin, UpdateView):

#     model = User
#     fields = []

#     def get_success_url(self):
#         return reverse("users:detail", kwargs={"username": self.request.user.username})

#     def get_object(self):
#         return User.objects.get(username=self.request.user.username)

#     def form_valid(self, form):
#         messages.add_message(
#             self.request, messages.INFO, _("Infos successfully updated")
#         )
#         return super().form_valid(form)


# user_update_view = UserUpdateView.as_view()


# class UserRedirectView(LoginRequiredMixin, RedirectView):

#     permanent = False

#     def get_redirect_url(self):
#         return reverse("users:detail", kwargs={"username": self.request.user.username})


# user_redirect_view = UserRedirectView.as_view()


def home_view(request):
    return render(request, "home.html")


class SignupView(View):
    form_class = CustomSignupForm
    template = "users/signup.html"

    def get(self, request, **kwargs):
        try:
            form = self.form_class()
            return render(
                request, self.template, {"form": form, "type": kwargs["name"]}
            )
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")

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
            print(e)

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
