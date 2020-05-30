from django_filters import rest_framework as filters

from apps.accounts import models as accounts_models
from apps.facility import models as facility_models


class FacilityFilter(filters.FilterSet):
    district = filters.filters.ModelMultipleChoiceFilter(
        field_name="district", queryset=accounts_models.District.objects.all()
    )

    class Meta:
        model = facility_models.Facility
        fields = {
            "positive_patient": ["exact", "range", "gt", "lt"],
            "negative_patient": ["exact", "range", "gt", "lt"],
            "total_patient": ["exact", "range", "gt", "lt"],
            "district": ["exact"],
        }


class InventoryFilter(filters.FilterSet):
    inventory_type = filters.CharFilter(field_name="item__name")
    facility_name = filters.CharFilter(
        field_name="facility__name", lookup_expr="istartswith"
    )
    required_quantity = filters.RangeFilter(
        field_name="required_quantity", lookup_expr="range"
    )
    current_quantity = filters.RangeFilter(
        field_name="current_quantity", lookup_expr="range"
    )

    class Meta:
        model = facility_models.Inventory
        fields = (
            "inventory_type",
            "facility_name",
            "required_quantity",
            "current_quantity",
        )
