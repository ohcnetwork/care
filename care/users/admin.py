from django import forms
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from djqscsv import render_to_csv_response

from care.users.forms import UserChangeForm, UserCreationForm
from care.users.models import (
    District,
    LocalBody,
    Skill,
    State,
    UserFlag,
    UserSkill,
    Ward,
)
from care.utils.registries.feature_flag import FlagRegistry, FlagType

User = get_user_model()


class ExportCsvMixin:
    @admin.action(description="Export Selected")
    def export_as_csv(self, request, queryset):
        queryset = User.objects.filter(is_superuser=False).values(
            *User.CSV_MAPPING.keys()
        )
        return render_to_csv_response(
            queryset,
            field_header_map=User.CSV_MAPPING,
            field_serializer_map=User.CSV_MAKE_PRETTY,
        )


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
                    "verified",
                )
            },
        ),
        *auth_admin.UserAdmin.fieldsets,
    )
    list_display = ["username", "is_superuser"]
    search_fields = ["first_name", "last_name"]

    def get_queryset(self, request):
        # use the base manager to avoid filtering out soft deleted objects
        qs = self.model._base_manager.get_queryset()  # noqa: SLF001
        if ordering := self.get_ordering(request):
            qs = qs.order_by(*ordering)
        return qs


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


@admin.register(UserFlag)
class UserFlagAdmin(admin.ModelAdmin):
    class UserFlagForm(forms.ModelForm):
        flag = forms.ChoiceField(
            choices=lambda: FlagRegistry.get_all_flags_as_choices(FlagType.USER)
        )

        class Meta:
            fields = (
                "user",
                "flag",
            )
            model = UserFlag

    form = UserFlagForm


admin.site.register(Skill)
admin.site.register(UserSkill)
