from django.contrib import admin

from apps.commons import models as commons_models


admin.site.register(commons_models.OwnershipType)
