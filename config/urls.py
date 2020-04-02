from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from config import api_router

from .auth_views import TokenObtainPairView
from .views import home_view

schema_view = get_schema_view(
    openapi.Info(
        title="Care API",
        default_version="v1",
        description="Api Documentation for Care",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="-"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path("", home_view, name="home"),
    path("ksdma/", TemplateView.as_view(template_name="pages/ksdma.html"), name="ksdma"),
    # API Docs
    url(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json",),
    url(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui",),
    url(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Rest API
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("care.users.urls", namespace="users")),
    # path("accounts/", include("allauth.urls")),
    path("facility/", include("care.facility.urls", namespace="facility")),
    # RESTful APIs
    path("api/v1/", include(api_router.urlpatterns)),
    url(r"^watchman/", include("watchman.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")},),
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")},),
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")},),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
