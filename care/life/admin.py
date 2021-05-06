from django.contrib import admin

from care.life.models import Job


class JobAdmin(admin.ModelAdmin):
    actions = ["silent_delete"]

    def silent_delete(self, request, queryset):
        queryset.delete()


admin.site.register(Job, JobAdmin)
