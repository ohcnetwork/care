from django.contrib.admin.apps import AdminConfig


class CareAdminConfig(AdminConfig):
    default_site = "config.admin.CareAdminSite"
