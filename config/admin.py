from binascii import Error as Base32Error
from time import time

from django import forms
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import BACKEND_SESSION_KEY, REDIRECT_FIELD_NAME, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import FormView
from django_ratelimit.core import is_ratelimited
from pyotp import TOTP

MFA_PENDING_SESSION_KEY = "admin_mfa_pending"
MFA_VERIFIED_SESSION_KEY = "admin_mfa_verified"
MFA_CHALLENGE_TIMEOUT = 5 * 60
RATE_LIMIT_MESSAGE = _("Too many attempts. Please try again later.")


def admin_ratelimited(request, group, account):
    # Admin authentication has a hard limit, without the API's CAPTCHA bypass.
    ip_limited = is_ratelimited(
        request,
        group=f"{group}-ip",
        key="ip",
        rate=settings.DJANGO_RATE_LIMIT,
        increment=True,
    )
    account_limited = is_ratelimited(
        request,
        group=f"{group}-account",
        key=lambda group, request: account,
        rate=settings.DJANGO_RATE_LIMIT,
        increment=True,
    )
    return ip_limited or account_limited


class AdminLoginView(LoginView):
    admin_site = None
    authentication_form = AdminAuthenticationForm
    template_name = "admin/login.html"

    def post(self, request, *args, **kwargs):
        username = get_user_model().normalize_username(
            request.POST.get("username", "").strip()
        )
        if admin_ratelimited(request, "admin-login", username):
            form = self.authentication_form(request=request, data={})
            form.add_error(None, RATE_LIMIT_MESSAGE)
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if user.is_mfa_enabled():
            return self.admin_site.start_mfa(
                self.request, user, user.backend, self.get_success_url()
            )
        self.request.session.pop(MFA_PENDING_SESSION_KEY, None)
        self.request.session.pop(MFA_VERIFIED_SESSION_KEY, None)
        return super().form_valid(form)


class AdminTOTPForm(forms.Form):
    code = forms.RegexField(
        regex=r"^[0-9]{6}$",
        label=_("Authentication code"),
        error_messages={"invalid": _("Enter a six-digit authentication code.")},
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "maxlength": 6,
            }
        ),
    )


@method_decorator(
    [login_not_required, sensitive_post_parameters("code"), csrf_protect, never_cache],
    name="dispatch",
)
class AdminTOTPView(FormView):
    admin_site = None
    form_class = AdminTOTPForm
    template_name = "admin/totp.html"
    http_method_names = ["get", "post", "options"]

    def dispatch(self, request, *args, **kwargs):
        self.pending = request.session.get(MFA_PENDING_SESSION_KEY, {})
        issued_at = self.pending.get("issued_at", 0)
        self.user = (
            get_user_model()
            .objects.filter(
                pk=self.pending.get("user_id"),
                is_active=True,
                is_staff=True,
            )
            .first()
        )
        if (
            not 0 <= time() - issued_at < MFA_CHALLENGE_TIMEOUT
            or not self.user
            or not self.user.is_mfa_enabled()
            or not self.user.totp_secret
            or self.pending.get("backend") not in settings.AUTHENTICATION_BACKENDS
            or not constant_time_compare(
                self.pending.get("state", ""), self.admin_site.mfa_state(self.user)
            )
        ):
            request.session.pop(MFA_PENDING_SESSION_KEY, None)
            return HttpResponseRedirect(
                reverse("admin:login", current_app=self.admin_site.name)
            )
        request.current_app = self.admin_site.name
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if admin_ratelimited(request, "admin-totp", str(self.user.pk)):
            form = self.form_class(data={})
            form.add_error(None, RATE_LIMIT_MESSAGE)
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        code = form.cleaned_data["code"]
        try:
            valid = TOTP(self.user.totp_secret).verify(code, valid_window=1)
        except (Base32Error, ValueError, TypeError):
            valid = False
        # An atomic cache marker also rejects concurrent reuse of an accepted code.
        replay_key = salted_hmac(
            "admin-totp-code", f"{self.pending['state']}:{code}"
        ).hexdigest()
        if not valid or not cache.add(
            f"admin-totp-used:{replay_key}", value=True, timeout=90
        ):
            form.add_error("code", _("Invalid or already used authentication code."))
            return self.form_invalid(form)

        auth_login(self.request, self.user, backend=self.pending["backend"])
        self.request.session.pop(MFA_PENDING_SESSION_KEY, None)
        self.request.session[MFA_VERIFIED_SESSION_KEY] = self.admin_site.mfa_state(
            self.user
        )
        return HttpResponseRedirect(
            self.admin_site.safe_next(self.request, self.pending.get("next"))
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **self.admin_site.each_context(self.request),
            "title": _("Two-factor authentication"),
            "subtitle": None,
            "has_permission": False,
        }


class CareAdminSite(AdminSite):
    @staticmethod
    def mfa_state(user):
        return salted_hmac(
            "admin-mfa-session",
            f"{user.pk}:{user.get_session_auth_hash()}:{user.totp_secret}",
        ).hexdigest()

    def has_permission(self, request):
        return super().has_permission(request) and (
            not request.user.is_mfa_enabled()
            or constant_time_compare(
                request.session.get(MFA_VERIFIED_SESSION_KEY, ""),
                self.mfa_state(request.user),
            )
        )

    def get_urls(self):
        return [
            path("totp/", AdminTOTPView.as_view(admin_site=self), name="totp"),
            *super().get_urls(),
        ]

    def safe_next(self, request, next_url):
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return reverse("admin:index", current_app=self.name)

    def start_mfa(self, request, user, backend, next_url):
        # Clear any previous authentication before creating the pending challenge.
        auth_logout(request)
        request.session[MFA_PENDING_SESSION_KEY] = {
            "user_id": str(user.pk),
            "backend": backend,
            "state": self.mfa_state(user),
            "issued_at": time(),
            "next": self.safe_next(request, next_url),
        }
        return HttpResponseRedirect(reverse("admin:totp", current_app=self.name))

    @method_decorator(never_cache)
    @login_not_required
    def login(self, request, extra_context=None):
        if request.method == "GET":
            if self.has_permission(request):
                return HttpResponseRedirect(
                    reverse("admin:index", current_app=self.name)
                )
            if super().has_permission(request) and request.user.is_mfa_enabled():
                return self.start_mfa(
                    request,
                    request.user,
                    request.session[BACKEND_SESSION_KEY],
                    request.GET.get(REDIRECT_FIELD_NAME),
                )

        request.current_app = self.name
        context = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
            **(extra_context or {}),
        }
        return AdminLoginView.as_view(
            admin_site=self,
            extra_context=context,
            next_page=reverse("admin:index", current_app=self.name),
        )(request)
