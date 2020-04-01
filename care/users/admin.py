from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from care.users.forms import UserChangeForm, UserCreationForm
from care.users.models import District, LocalBody, Skill, State

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
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
                    "gender",
                    "age",
                    "skill",
                    "verified",
                )
            },
        ),
    ) + auth_admin.UserAdmin.fieldsets
    list_display = ["username", "is_superuser"]
    search_fields = ["first_name", "last_name"]


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    pass


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    pass


@admin.register(LocalBody)
class LocalBodyAdmin(admin.ModelAdmin):
    pass


admin.site.register(Skill)
