from django.contrib.admin import AdminSite
from django.utils.translation import ugettext_lazy as _


class CustomLoginAdminSite(AdminSite):
    site_title = _("My site admin")
    site_header = _("Administration")
    index_title = _("CustomLogin")
    # registering Custom login form for the Login interface
    # this login form uses CustomBackend
    login_form = CustomLoginForm


# create a Admin_site object to register models
admin_site = CustomLoginAdminSite()
