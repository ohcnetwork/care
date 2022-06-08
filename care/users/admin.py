import csv

from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from djqscsv import render_to_csv_response

from care.users.forms import UserChangeForm, UserCreationForm
from care.users.models import District, LocalBody, Ward, Skill, State, UserSkill

User = get_user_model()


class ExportCsvMixin:
    def export_as_csv(self, request, queryset):

        queryset = User.objects.filter(is_superuser=False).values(*User.CSV_MAPPING.keys())
        return render_to_csv_response(
            queryset, field_header_map=User.CSV_MAPPING, field_serializer_map=User.CSV_MAKE_PRETTY,
        )

    export_as_csv.short_description = "Export Selected"


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin, ExportCsvMixin):
    form = UserChangeForm
    add_form = UserCreationForm
    actions = ["export_as_csv"]
    fieldsets = (
        (
            "User",
            {
                "fields": (
                    "user_type",
                    "local_body",
                    "district",
                    "state",
                    "phone_number",
                    "alt_phone_number",
                    "gender",
                    "age",
                    "verified",
                )
            },
        ),
    ) + auth_admin.UserAdmin.fieldsets
    list_display = ["username", "is_superuser"]
    search_fields = ["first_name", "last_name"]


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    autocomplete_fields = ["state"]


@admin.register(LocalBody)
class LocalBodyAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    autocomplete_fields = ["district"]


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    autocomplete_fields = ["local_body"]


admin.site.register(Skill)

admin.site.register(UserSkill)
