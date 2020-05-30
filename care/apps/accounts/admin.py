from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext as _

from import_export.admin import ImportExportModelAdmin

from apps.accounts import (
    models as accounts_models,
    forms as accounts_forms,
)


class StateAdmin(ImportExportModelAdmin):
    search_fields = ("name",)


class UserTypeAdmin(ImportExportModelAdmin):
    search_fields = ("name",)


class DistrictAdmin(ImportExportModelAdmin):
    raw_id_fields = ("state",)
    search_fields = ("name",)


class LocalBodyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "body_type",
    )
    raw_id_fields = ("district",)
    search_fields = ("name",)


class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class UserModelAdmin(UserAdmin):

    form = accounts_forms.UserChangeForm
    add_form = accounts_forms.UserCreationForm

    list_display = ("first_name", "last_name", "email", "active", "user_type")
    list_display_links = (
        "first_name",
        "last_name",
        "email",
    )
    list_filter = ("active",)

    search_fields = (
        "first_name",
        "last_name",
        "email",
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "age",
                    "gender",
                    "phone_number",
                ),
            },
        ),
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "phone_number",
                    "user_type",
                    "age",
                    "gender",
                    "skill",
                    "verified",
                    "district",
                    "state",
                    "local_body",
                )
            },
        ),
        (_("Permissions"), {"fields": ("active",)}),
        (_("Important dates"), {"fields": ("last_login",)}),
    )
    filter_horizontal = []

    ordering = ("email",)


admin.site.register(accounts_models.State, StateAdmin)
admin.site.register(accounts_models.District, DistrictAdmin)
admin.site.register(accounts_models.LocalBody, LocalBodyAdmin)
admin.site.register(accounts_models.Skill, SkillAdmin)
admin.site.register(accounts_models.User, UserModelAdmin)
admin.site.register(accounts_models.UserType, UserTypeAdmin)
admin.site.register(accounts_models.UserDistrictPreference)
