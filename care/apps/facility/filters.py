from django_filters import rest_framework as filters

from apps.facility import models as facility_models


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
