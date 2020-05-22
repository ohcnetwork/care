from django_filters import rest_framework as filters

from apps.accounts import models as accounts_models


class DistrictFilter(filters.FilterSet):
    state = filters.CharFilter(field_name='state__id')

    class Meta:
        model = accounts_models.District
        fields = ('state',)
