from django import forms
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from care.users.forms import UserChangeForm, UserCreationForm
from care.users.models import UserFlag
from care.utils.registries.feature_flag import FlagRegistry, FlagType

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    actions = ["export_as_csv"]
    fieldsets = (
        (
            "User",
            {
                "fields": (
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
